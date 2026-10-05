# PlanExe-skill: conversion report

This report tracks the port of PlanExe's Luigi pipeline (73 stages) to skills run by the
`planexe_skill` DAG, with the verification results and every regression/tweak found on the way.

## Method

**Per-stage verification** (`python3 -m verify.eval_stage STAGE`), on 4 dev baselines from
PlanExe-web: `20250706_gibraltar_tunnel`, `20260516_datacenter_in_france`,
`20260514_cross_border_rail_ticketing`, `20260202_heatwave_resilience`.

1. Copy the baseline run into `.verify_work/stage_runs/<stage>/<baseline>/`, delete only that
   stage's outputs. All upstream files are the baseline's own, so a stage is judged in isolation
   and earlier stages never need to be regenerated.
2. Run the stage with `python -m planexe_skill`-equivalent `Runner(only=[stage])`.
3. Structure check: every output file exists; JSON shape (keys + value types, recursively; list
   lengths ignored; `metadata`/prompt fields only checked for presence) equals the baseline's;
   markdown headings that appear in *all* baselines (i.e. template headings) must appear.
4. Quality: blind pairwise judge (Sonnet 5.5) on the stage's human-facing output(s), run twice
   with A/B positions swapped. Agreement → that verdict; win+tie → win; win+loss → tie.
   Deterministic stages (no LLM) must be byte-identical instead.

A stage passes when structure matches and it wins or ties on at least 3 of 4 baselines.

**Caveats.** The baselines were generated with `gemini-2.5-flash-lite` (gibraltar with
`ling-3.0-flash`), much smaller models than Sonnet 5.5 / Haiku 4.5, so wins are expected where the
model matters. The judge is also a Claude model judging Claude output against Gemini output;
self-preference bias is possible, which is why the judge prompt is explicit about criteria
(faithfulness to the prompt, specificity, correctness, format fitness, downstream usefulness, no
credit for verbosity) and why each comparison is position-swapped. Spot checks of the judge
rationales are recorded below where they influenced a decision.

## Runtime findings

- **Auth inside Claude Code.** When the runner is started from within Claude Code (desktop app),
  the parent injects `CLAUDE_CODE_*` and `ANTHROPIC_BASE_URL` variables that route the CLI to the
  host's private auth channel; a spawned `claude -p` then fails with "OAuth session expired".
  `ClaudeCLIBackend` strips those variables so the child uses the user's own login.
- **Sandbox.** In a sandboxed shell the child CLI cannot reach the macOS keychain and fails the
  same way. Runs must happen outside the sandbox (documented in README/CLAUDE.md).
- `claude -p --json-schema` handles pydantic-style schemas with `$defs`/`$ref`, `anyOf` nulls and
  enums, so PlanExe's pydantic models are carried over as JSON schema files unchanged
  (extracted with `tools/extract_planexe_module.py`, a dev-only helper run in PlanExe's venv).
- Smoke run of the first 8 stages through the real runner: 14 LLM calls, 74 s wall clock with
  4 workers; the critical-path ETA started at 1m29s.

- **Child CLI isolation (important).** A plain `claude -p` inherits the user's Claude Code
  configuration: `effortLevel` from `~/.claude/settings.json` (here "high", so Haiku calls ran with
  extended thinking and produced 20k-60k output tokens / up to 30 min per call), enabled plugins,
  SessionStart hooks that inject text into the context (~7k extra input tokens per call), MCP
  servers and skills. The backend now runs every call with `--setting-sources project` in an empty
  working directory, `--strict-mcp-config`, `--disable-slash-commands`, `--tools ""` and an
  explicit `--effort` per tier (high: `high`, low: `low`). Measured on a small call: input tokens
  7,963 -> 912. System prompts are passed with `--system-prompt-file` (review_plan's system prompt
  is ~440 KB, close to the OS argument-size limit).
- **Thinking off outside the reasoning block.** Even with `--effort low`, Haiku spent 2-3x the
  visible output on hidden thinking (find_team_members: 16k output tokens for ~4k visible). Tiers
  are now: `high` = Sonnet 5.5 + `--effort high` for the first 19 LLM stages (screening through
  `selected_scenario_constraint`); `low` = Haiku 4.5 with thinking disabled
  (`--settings {"alwaysThinkingEnabled": false}` + `MAX_THINKING_TOKENS=0`) for everything after;
  `mid` = Sonnet without thinking, used only where an eval showed Haiku is not good enough
  (filter_documents_to_create). On a test call this halved latency (15.9 s -> 7.8 s).
- **Transient CLI errors.** `structured_output_retry_exhausted` (seen with Haiku on 20k+ token
  structured outputs) and mid-response server errors are retried with backoff by the backend.
- **Fail fast instead of waiting.** Some calls used to take 25-30 minutes before failing: the CLI
  silently re-generated a rejected structured output (~4 min per attempt for 20k-token answers), the
  per-call timeout was 15 min and timeouts were retried 3 times. Now every call streams
  (`--output-format stream-json --include-partial-messages`); no stream event for 90 s = stalled,
  killed; hard cap 10 min; a stall/timeout is retried once; the CLI may re-try a rejected
  structured output once (`--max-turns 4`, rejection events counted) and then the backend switches
  to plain-JSON mode with local schema validation and the problems fed back.
- **Resume points.** Every completed LLM call is cached under
  `RUN_DIR/.planexe_skill/llm_cache/<stage>/`. A stage that fails at call 15 of 16 replays the
  first 14 instantly when re-run. The cache is deleted when the stage succeeds (and on `--force`).
- **Note on earlier per-stage evals.** Stages evaluated before the isolation fix ran with the
  user's settings leaking into the child (high effort for Haiku, hook text in context). Their
  verdicts stand as recorded; the end-to-end runs below use the isolated backend.

## Stage log

### Group (a): stages 0-9 — prompt screening and classification (tier high, Sonnet 5.5 + high effort)

`start_time` and `initial_plan_raw` are not skills: they are the run's root inputs
(`start_time.json`, `plan_raw.json`) written by `python -m planexe_skill create`, exactly as
PlanExe's web app writes them before starting Luigi.

| stage | notes |
|---|---|
| setup | deterministic, byte-identical to all baselines |
| screen_planning_prompt | verbatim port |
| extract_constraints | verbatim port |
| identify_purpose | verbatim port |
| premise_attack | verbatim port; the 5 lenses now run in parallel (PlanExe ran them sequentially) |
| redline_gate | **tweak**: see below |
| classify_domain | verbatim port of the 2-pass (candidates + primary selection) algorithm |
| plan_type | verbatim port |

**redline_gate regression → fixed.** First run: verdicts matched the baseline on all four plans,
but the judge preferred the baseline on 3/4. Cause: PlanExe's schema says `rationale_short` "Must be
exactly 'The prompt is safe' when verdict=ALLOW", while its system prompt asks for "One concise
sentence explaining your decision". Gemini followed the system prompt; Claude followed the schema
literally, producing an uninformative rationale. Nothing downstream parses that string, so the
schema description was aligned with the system prompt. Re-run: 4/4 wins.


### Group (b): levers and scenarios (tier high)

All prompts and schemas verbatim. The six `*_constraint` stages share
`planexe_skill/shared/constraint_checker.py` (PlanExe's ConstraintChecker).

| stage | notes |
|---|---|
| potential_levers | Verbatim adaptive loop (up to 5 calls until >= 15 levers, "Generate 5 to 7 MORE levers" follow-ups), pydantic validators re-implemented, per-lever constraint checks with violation history fed back. Tweak: the per-lever checks of one call run concurrently. 4/0/0 |
| potential_levers_constraint | shared checker. 4/0/0 |
| triage_levers | verbatim; failed call keeps all levers as secondary (as PlanExe). 4/0/0 |
| enrich_levers | batches of 5, split-and-retry on failure. Tweaks: batches run concurrently; the stage fails if no lever could be enriched (PlanExe silently wrote an empty list). 4/0/0 |
| triaged_levers_constraint | shared checker. 4/0/0 |
| enriched_levers_constraint | shared checker. 3/0/1 — gibraltar loss: same verdicts, judge preferred baseline's citations; one-off stray quote in a summary. |
| focus_on_vital_few_levers | verbatim incl. batched fallback. 3/0/1 — gibraltar loss traced to PlanExe's own fill rule (5 slots Critical->High->Medium->Low, list order). The baseline file mislabels lever ids on 2 plans; ours match the input. |
| candidate_scenarios | verbatim. 4/0/0 |
| strategic_decisions_markdown | deterministic, byte-identical 4/4 |
| vital_few_levers_constraint | shared checker. 4/0/0 |
| candidate_scenarios_constraint | shared checker. 4/0/0 |
| select_scenario | verbatim. 4/0/0 |
| scenarios_markdown | deterministic, byte-identical 4/4 |
| selected_scenario_constraint | shared checker. 4/0/0 |

### Group (c): assumptions -> project plan (tier high)

Offline replay check: given baseline inputs every stage rebuilds byte-identical system/user prompts;
given baseline responses every renderer reproduces the baseline markdown byte-for-byte.

| stage | notes |
|---|---|
| physical_locations | verbatim; digital plans skip the LLM and write PlanExe's stub (branch untested: all baselines are physical). 4/0/0 |
| currency_strategy | verbatim (`CURRENCY_STRATEGY_SYSTEM_PROMPT_2`). 4/0/0 |
| identify_risks | verbatim. 4/0/0 |
| make_assumptions | verbatim incl. current-year placeholder. 4/0/0 |
| distill_assumptions | verbatim; reads `make_assumptions.json` like PlanExe. 4/0/0 |
| review_assumptions | verbatim, 9 document chunks. 4/0/0 |
| consolidate_assumptions_markdown | full file deterministic (byte-identical); short file = 9 parallel ShortenMarkdown calls. **Regression -> fixed:** Sonnet renamed/promoted headings, failing the structure check; two lines added to the shorten prompt (keep existing heading wording/level; turn label lines into `##` headings). 0/4/0 |
| pre_project_assessment | verbatim. 4/0/0 |
| project_plan | verbatim except one sentence. **Regression -> fixed:** gibraltar lost twice; Sonnet read "no specific date unless specified by the user" literally and gave an undated timeline although plan.txt states today's date and "Project start ASAP". Added: a stated current date plus a stated start counts as specified. 3/1/0 |

### Group (d1): WBS level 1, governance, related resources

| stage | notes |
|---|---|
| create_wbs_level1 (high) | verbatim (no system prompt, query preamble as PlanExe). 3/1/0 |
| governance_phase1_audit (low) | verbatim. 4/0/0 |
| related_resources (low) | verbatim. 3/0/1 — gibraltar loss: Haiku hallucinated details of real reference projects (model knowledge). |
| governance_phase2_bodies (low) | verbatim. 2/1/1 — gibraltar: 8 bodies with inconsistent thresholds vs baseline's 6. Intermittent `structured_output_retry_exhausted` -> now retried by the backend. |
| governance_phase3_impl_plan (low) | verbatim. 3/1/0 |
| governance_phase4_decision_escalation_matrix (low) | verbatim. 4/0/0 |
| governance_phase5_monitoring_progress (low) | verbatim. 4/0/0 |
| governance_phase6_extra (low) | verbatim. 4/0/0 |

### Group (d2): team, SWOT, expert review, data collection (tier low)

| stage | notes |
|---|---|
| find_team_members | verbatim. 3/0/1 — gibraltar: missing geotechnical/rail role. |
| enrich_team_members_with_contract_type | **Regression -> tweak:** Haiku labelled every role full-time on 3/4 plans (1/0/3). Added one generic sentence: decide each role on its merits (workload continuity, count, scale/cancellation risk). 1/2/1 |
| enrich_team_members_with_background_story | verbatim. 3/0/1. Structure flag on datacenter is a baseline defect (baseline LLM returned ids 101-107 for 1-8, so PlanExe merged nothing); not imitated. |
| enrich_team_members_with_environment_info | verbatim. 2/2/0 |
| review_team | verbatim (vendored TeamMarkdownDocumentBuilder). 3/1/0 |
| team_markdown | deterministic, byte-identical 4/4 |
| swot_analysis | verbatim purpose-specific prompts. 1/3/0 |
| expert_review | verbatim; the finder's chat follow-up is embedded as prior conversation; one retry per call (mirrors PlanExe's LLMExecutor). 3/1/0 |
| data_collection | verbatim. 3/0/1 — gibraltar: Haiku returned 4 items vs 14 (single-run variance). |

### Group (e): documents, WBS level 2/3, durations, pitch

Replay check with a fake backend answering the baseline responses: byte-identical prompts, same
call counts, identical outputs except uuids/metadata.

| stage | notes |
|---|---|
| identify_documents (low) | verbatim, purpose-specific prompts. 4/0/0 |
| create_wbs_level2 (high) | verbatim + **tweak (run time):** Sonnet produced 11-17 phases / 77-123 subtasks (baselines 3-7 / 17-35), tripling the level-3 and duration fan-out. The preamble now asks for planning granularity (typically 4-8 phases x 3-6 subtasks): 33-44 subtasks. 4/0/0 |
| filter_documents_to_create | **switched to tier high**: Haiku rated most documents Critical with summary counts inconsistent with its ratings; a calibration prompt didn't fix it. Sonnet, verbatim prompts: 4/0/0 |
| filter_documents_to_find (low) | verbatim. 2/2/0 |
| identify_task_dependencies (low) | verbatim. 3/0/1 (gibraltar 6.0 vs 6.5) |
| draft_documents_to_create (low) | verbatim, per-document calls in parallel. 4/0/0 |
| draft_documents_to_find (low) | same. 4/0/0 |
| create_pitch (low) | verbatim. 2/2/0 |
| estimate_task_durations (low) | verbatim, chunks of 3 in parallel. 3/1/0 |
| convert_pitch_to_markdown (low) | **tweak:** Haiku turned `why_this_pitch_works` into meta sections and dropped Target Audience (1/0/3); 3 lines fix the field->section mapping. 3/1/0 |
| create_wbs_level3 (low) | verbatim, one call per level-2 subtask in parallel. 4/0/0 |

### Group (f): final review (tier low)

| stage | notes |
|---|---|
| review_plan | verbatim 16 sequential questions (each sees the previous Q&A). **Regression -> tweak:** Haiku's answers grew from ~1K to 5K chars over the conversation, merged bullets and invented "since Version 1" history (1/2/1). A short reminder next to each question (exactly 3 bullets, ~80 words each, no invented facts) fixed it. 4/0/0 |
| executive_summary | verbatim. 4/0/0 |
| questions_and_answers | verbatim (2 calls). 3/1/0 |
| prompt_adherence | verbatim (directive extraction + scoring). 3/1/0 |
| premortem | verbatim 3-call chat. **Regression -> guard:** gibraltar re-emitted A1-A3 in a follow-up, duplicating failure modes; follow-ups that repeat earlier assumption ids are now de-duplicated. 4/0/0 |
| self_audit | verbatim (physics check + 19 checklist items; regenerated system prompts identical to the baselines). Sequential: every item sees all previous answers. 4/0/0 |

### Deterministic stages

| stage | notes |
|---|---|
| wbs_project_level1_and_level2, wbs_project_level1_and_level2_and_level3 | vendored WBSPopulate/CreateWBSTableCSV; byte-identical 4/4 |
| create_schedule | vendored PlanExe scheduler + DHTMLX exporter (pandas replaced by `csv`); byte-identical 4/4 |
| consolidate_governance, markdown_with_documents_to_create_and_find | byte-identical 4/4 |
| report | Python-Markdown and pandas replaced by a stdlib renderer (`planexe_skill/shared/markdown_html.py`). report.md identical except timestamp; report.html matches the baseline's tag profile (headings, lists, tables, emphasis within 2%) on 3/4. heatwave's baseline report was produced by an older PlanExe report generator (different sections). PlanExe-web's injected Google Analytics tags are ignored in the comparison. |

### Reference DAG discrepancies

`docs/reference/planexe_pipeline_dag.json` (generated by PlanExe's `extract_dag`) lists several
inputs that the node code does not actually read. The skills follow the node code. Main cases:
most stages after the assumptions read `consolidate_assumptions_short.md` (not `_full`); many read
`project_plan_raw.json` / `identify_purpose_raw.json` / earlier `*_raw.json` files instead of the
markdown; the six constraint stages read `extract_constraints_raw.json`; the final review stages
read `wbs_project_level1_and_level2_and_level3.csv` and also `review_plan.md`,
`questions_and_answers.md`, `premortem.md`; `expert_review` also writes `experts_raw.json`,
`experts.json` and `expert_criticism_{n}_raw.json`.

## Status (2026-10-05) and next steps

- All 71 stages are ported and verified per stage against the 4 dev baselines (see Results).
- **Word budget.** Non-reasoning tiers get "At most 160 words" on every free-text field that has no
  PlanExe length hint (configurable per skill via `max_words_per_field`), plus one conciseness line in
  the system prompt. Re-verified on the 22 most verbose stages: all pass, several improved
  (project_plan, make_assumptions, data_collection 4/0/0; pre_project_assessment 1/2/1 -> 3/1/0).
- **First solo end-to-end run (battery_breakthrough), aborted by the user at 67/71 stages:**
  50 min elapsed, 220 LLM calls, 0 failures. Remaining were questions_and_answers, premortem,
  self_audit, report. Largest single calls: data_collection 9m31s, identify_documents 7m58s,
  questions_and_answers > 5m, review_plan 4m23s (16 calls), create_wbs_level3 4m06s (60 calls).
- **Next:** (1) tighten budgets on the few long single calls on the critical path (data_collection,
  identify_documents, questions_and_answers, premortem) to bring a full run under 45 min;
  (2) finish the 4 end-to-end verification runs (euro_adoption, battery_breakthrough,
  gibraltar_tunnel, datacenter_in_france) with `python3 -m verify.eval_run`;
  (3) `~/.planexe_skill/timings.json` still contains durations recorded under eval load (fixed for
  future evals); delete it so ETAs re-learn from real runs.
- Resuming the aborted run: `python3 -m planexe_skill run runs/battery` continues with the 4
  remaining stages (finished stages are clean in the manifest).

### Fact-checking in the reasoning tier (2026-10-05)

**Correction (2026-10-05):** the "0 web searches" figures below were a measurement bug: the backend read `usage.server_tool_use.web_search_requests`, which stays 0 because the CLI runs WebSearch as its own tool. The count now comes from the WebSearch tool calls in the stream; with searching required, premise_attack makes 2-3 searches per lens. Whether the earlier runs searched is unknown.

Reasoning-tier calls may use the `WebSearch` tool (`--tools WebSearch`, at most 3 searches per call,
only for claims the answer depends on and the model is unsure of). Enabled for the stages that make
real-world claims: premise_attack, potential_levers, enrich_levers, candidate_scenarios,
select_scenario. Classification and constraint-check stages opt out (`fact_check: false`).
Everything downstream stays single-shot without tools. The four longest single-call stages
(data_collection, identify_documents, questions_and_answers, premortem) got a tighter budget of
80 words per field (not re-verified per stage, to save tokens).

### End-to-end run: battery_breakthrough (2026-10-05)

One plan, generated alone with 4 workers (`runs/battery`, not committed). The CLI login was revoked
mid-run (401), which failed 3 stages; after `claude auth login` the run resumed with the remaining 20
stages (the runner now stops the whole run on an auth error instead of letting stages fail one by one).

- **Complete:** 71/71 stages, `report.html` (1.75 MB) and `report.md`; 0 failures after resuming.
- **LLM calls:** 231 successful (fan-out made it a little above the ~200 estimate); 581k output tokens.
- **Wall clock:** ~34 min (51 stages) + 40.5 min (20 stages) ≈ 75 min, including time lost to the
  revoked login. Still above the 45-minute target.
- **Structure vs the PlanExe baseline (no LLM):** same file set (plus report.md, which the older
  baseline predates) and 71/71 stages with the same JSON/markdown structure; the only flagged
  difference is candidate_scenarios' `lever_settings`, whose keys are lever names (content).
- **Fact-checking:** 0 web searches. Searching was optional ("none if you are confident") and the
  model never chose to search. To actually fact-check, make it mandatory for premise_attack's
  evidence and potential_levers' key facts.
- **Slowest stages (critical path candidates):** data_collection 9m55s (1 call; the per-field budget
  doesn't limit its many list fields), premortem 9m23s (3 sequential calls), identify_documents
  6m16s (1 call), self_audit 6m10s (19 sequential calls), review_plan 4m39s (16 sequential calls),
  create_wbs_level3 3m59s (48 calls), expert_review 3m30s, potential_levers 3m32s.
- **Next:** cap list lengths in data_collection / identify_documents / premortem, mandatory
  fact-checking in 2 stages, then judge this plan against its baseline (`python3 -m verify.eval_run
  runs/battery 20250724_battery_breakthrough`, ~140 Sonnet judge calls) if the token budget allows.

### Report comparison: battery_breakthrough vs PlanExe baseline (2026-10-05)

Section-level comparison of the generated report against the baseline report (metrics + targeted reading;
no LLM judge). Ordered by severity.

1. **Gantt length (not a defect).** The Gantt spans 26.1 years vs 7.0 because it is a deliberate
   unoptimized waterfall (no information about resources for parallel work) and this run has 56
   level-2 tasks (baseline 30) with a higher median duration (120 vs 87.5 days).
2. **Unverified numbers harden into specs (high).** identify_risks (Haiku, no thinking, no fact
   check) wrote an illustrative "e.g. no runaway onset <60 °C"; downstream stages turned it into
   specs ("≥62 °C ±3 °C", "≥70 °C") that reach the Executive Summary. Physically dubious (60 °C is
   around a cell's normal upper operating temperature). Fix: fact-check in the assumptions block
   (identify_risks, make_assumptions), and tell downstream stages not to promote examples to
   requirements.
3. **No fact-checking happened (high).** 0 web searches; premise_attack's evidence uses real cases
   (DOE Battery500, Oxis Energy, Cuberg/Northvolt) but details contradict each other across lenses
   (launch 2016 vs 2017; 223/192/196 layoffs; August vs October 2024). Fix: mandatory 1-2 searches
   for evidence/key facts.
4. **Prompt adherence rubber-stamps (medium).** Extracts 6 directives (baseline 9: separately
   checkable budget/timeline/location constraints) and scores 100% with no issues (baseline 98% with
   one partial). Fix: tier mid, or ask for atomic directives.
5. **Report length / reading burden (medium).** Total report ~2x the baseline; project_plan 17x,
   governance 6x, documents 7x, data_collection 7x, WBS 4.6x. Lists are unbounded even with the
   per-field word budget. The per-stage judge liked the depth, but an executive reader won't.
   Fix: list-length caps (e.g. maxItems hints) and a tighter executive_summary (1,539 vs 460 words).
6. **Small date-arithmetic slips (low).** Executive summary: "month 72 (February 2033)" for a May 2026
   start (should be ~May 2032).

What holds up: budget (USD 300M), location (Austin) and the 7-year horizon are stated consistently
across executive summary, pitch, project plan, SWOT and premortem; structure matches the baseline on
71/71 stages; content is far more specific than the baseline (named precedents, measurable criteria).

### External review (Codex) of the same two reports

Codex scored the new report 8.9/10 vs 6.0/10 for the baseline (portfolio optionality, validation
rigor, anti-sunk-cost governance, budget discipline all much stronger), with three regressions:
calendar arithmetic ("Month 72 (February 2033)" for a May 2026 start), falsely precise numbers
presented as facts, and lower signal-to-noise (verbosity).

Responses:
- **Calendar:** every LLM call now gets a "Month N = date" table computed from `start_time.json`,
  and every LLM result is post-processed by `planexe_skill/calendar_fix.py`, which recomputes the date
  attached to "Month N (...)" as start + N months (keeps the model's date style). Prompting alone did
  not work: a re-generated project_plan (Haiku, no thinking) still had 14/22 wrong pairs.
- **Calendar fix measured on the existing battery report (no LLM calls):** applying
  `calendar_fix` to a copy of the run's stage outputs and regenerating only the deterministic
  `report` stage took month/date pairs in report.md from 67 correct / 123 wrong to 186 correct /
  4 flagged (the 4 are scanner false positives: ranges and dates belonging to a neighbouring month
  number). Handled forms: "Month N (date)", "month N, date", "month N = date", "month N gate (date)",
  and reversed "date (month N)", in full-name, abbreviated and ISO styles. In new runs the same pass
  runs on every LLM result.
- **Second Codex review** (of the corrected report): schedule consistency 4-5 -> 8.0, overall ~9.1.
  Remaining leaks were fractional/fuzzy months ("month 3.5 (mid-July 2026)") and dates with no month
  offset ("by July 2", "through February 2033"). Following Codex's suggestion the model now writes
  time only as "Month N" (fractions and ranges allowed; prompt rule) and the normalizer appends the
  computed date to every bare offset ("Month 3 (2026-08-02)", "Months 48-72 (2030-05-02 to
  2032-05-02)"), recomputes paired dates incl. fractional and mid-/early-/late- forms, and no longer
  lets a date paired with one offset be re-assigned to the next one. On the battery copy: 187 correct,
  3 scanner false positives. Dates without any month offset in the existing report (9x "by July 2",
  1x "through February 2033") can't be fixed after the fact; the prompt rule addresses new runs.
- **Third Codex review:** schedule consistency ~9/10; "the remaining problems look like
  post-processing/parser coverage and stale redundant prose, not reasoning failures". Its edge cases
  are now handled: lists ("months 18, 36, 54, 72 (2027-11-02, ...)"), singular ranges
  ("month 9-12"), "= date" instead of nested parentheses inside an existing parenthesis, and a stale
  date-only parenthetical directly after a computed date is dropped ("(through February 2033)").
  Still unfixable after the fact: absolute dates with no month offset ("lock protocol by July 2,
  2026"); new runs are told to write "Month N" only.
- **Provenance:** a rule asking to tag non-user, non-benchmark figures as "(proposed threshold)" /
  "(estimate)" and never to promote "e.g." values to requirements is appended to every user message.
  Haiku without reasoning largely ignores it (1 tag in an 8,000-word project plan); a structural fix
  (e.g. a `basis` field next to numeric fields in the schemas of the assumption stages) is still open.
- **Verbosity:** open (list-length caps).

### End-to-end run: datacenter_in_france (2026-10-05)

Same prompt and start date as the PlanExe baseline, generated alone with 4 workers, first full run
with the calendar normalizer and the "Month N only" rule.

- **Completes end to end:** 71/71 stages, 0 failures, 208 LLM calls, 748k output tokens,
  **1h29m** (target 45 min). Slowest: review_assumptions 13m08s, self_audit 9m45s,
  data_collection 9m36s, premortem 6m32s, identify_documents 5m57s, review_plan 5m31s,
  potential_levers 5m26s.
- **Structure:** 67/71 stages identical in shape to the baseline. Flags: candidate_scenarios
  (lever names as keys: content), background_story/environment_info (baseline defect, see group d2),
  and consolidate_assumptions_short dropped the "## Location 1/2" headings (minor regression).
- **Dates:** 260/260 month/date pairs correct; 2,438 month offsets annotated with computed dates.
- **Strategy:** both pick a staged, gate-driven scenario. The new plan carries the red-team brief
  through the whole report (kill criteria mentioned 125x vs 3x, "no-build" alternative 13x vs 1x,
  downsizing 182x vs 6x) and names plausible local specifics (RTE connection queue, Gravelines,
  CNIL); the Cattenom misplacement seen in an earlier SWOT eval is absent.
- **Prompt adherence:** 15 directives in both; 99% vs 94%, both with an issues section.
- **Weak:** length. The report is 3.1x the baseline (152k vs 48.5k words), the executive summary
  4.7x (1,973 vs 422 words). Provenance tags are almost unused (1x "proposed threshold", 4x
  "estimate"). Fact-checking ran 0 web searches.

### Codex review of the datacenter run

Codex: 8.8/10 vs 7.4/10 for the PlanExe baseline ("here is a system for determining whether this
enormous project deserves to exist" vs "a plausible strategy"). Strongest gains: gates/kill criteria,
governance (independent gate authority), execution depth (272 vs 89 WBS rows), scenario/fallback
quality. Weaknesses it found:

1. **Two clocks.** "Month 5 (October 2026), immediately" next to deadlines in July 2026. Cause: the
   run reused the baseline's start date (2026-05-16) for comparability, while the `claude` CLI tells
   the model the real date (2026-10-05). In normal use (`create` stamps today's date) they agree.
   Fixed anyway: every call now states the plan's "today" (= Month 0) and to ignore any other date.
2. **Unreconciled financials.** EUR 70-80/MWh tenant pricing vs EUR 140-160/MWh electricity vs
   >EUR 3B/yr Phase 1 revenue and 10-12% IRR are not consistent (energy-only price component vs
   total price never distinguished). Open.
3. **Conflicting gate thresholds** across sections (Phase 1 vs Phase 2 criteria occasionally mixed).
   Open.
4. **Signal-to-noise:** ~3.3x the baseline's text; the central decision tree gets buried.

Codex's proposals (not implemented): a final cross-report consistency pass (prices, units, gate
percentages, deadlines vs "now") and a one-page "decision kernel" up front (the 4-5 yes/no
questions whose NO means delay/split/downsize/stop).

### Fixes after the datacenter review (2026-10-05)

- **New stage `consistency_review`** (1 reasoning call, not in the original PlanExe): a decision
  kernel (3-6 go/no-go questions with thresholds, evidence, and what a NO means) and up to 12
  cross-document contradictions with severity and suggested resolution. Rendered as the report's first
  section. On the datacenter run it surfaced e.g. committee seated Month 1 (project plan) vs Month 5
  (executive summary), RTE >250 MW (pitch) vs >=500 MW (executive summary) vs <300 MW fail line
  (premortem), and three different small-scale fallback sizes.
- **Length:** list-length caps (`max_items_per_list`) for project_plan, executive_summary,
  governance phases (except the implementation plan), data_collection, review_assumptions; executive
  summary at 60 words per field. Re-generated on the datacenter run: executive summary 1,973 -> 935
  words (baseline 422), project plan 6,702 -> 4,357 words.
- **Structured-output failover on the first rejection** (was: after the CLI's own retry). The 13-minute
  review_assumptions call had consumed 93k input tokens for 16k output tokens, i.e. the CLI regenerated
  the whole answer about twice.
- **Fact-checking:** `fact_check: required` for premise_attack (verify cited precedents); measured
  2-3 searches per lens. Search counting fixed (see correction above).
- **Plan date:** past/future plan dates are supported by design; every call states the plan's
  "today" (Month 0).

### Canonical facts (2026-10-05)

Codex's next step after the consistency check: repair, don't just report. New stage `canonical_facts`
(1 reasoning call) reconciles 15-40 key facts (gates, prices with unit and meaning, caps, milestones as
Month N; each tagged user constraint / decision / proposed threshold / estimate). It runs right before
project_plan; all later LLM stages declare `canonical_facts.json` as input and get the table appended to
their user message with "the canonical fact wins". project_plan moved to tier mid (Sonnet, low effort).

What the iterations showed (datacenter prompt):
- Facts placed *after* project_plan (full run `runs/datacenter2`, 73 stages, 0 failures, 233 calls,
  1h12m, 15 web searches, 47 facts): 13 contradictions remained; later stages sided with the
  unreconciled project plan (Phase 1 FID Month 12 vs canonical Month 24).
- Facts *before* project_plan, in the system prompt, project_plan on Haiku: still 12; Haiku ignored them.
- Facts in the *user message*, project_plan on Sonnet (targeted re-run of 5 stages): the executive
  summary, project plan and pitch now agree with the canonical facts; the 12 remaining conflicts are
  against the pre-reconciliation assumptions (by design) and against review/premortem/self-audit files
  that this partial check did not regenerate. consistency_review now treats assumption-vs-fact
  differences as expected unless a later document follows the old value.

### Full run with facts before project_plan: datacenter_in_france (`runs/datacenter3`)

- 73/73 stages, 0 failures, 212 LLM calls, 18 web searches, **1h16m**; 43 canonical facts;
  report 132k words (previous full run 152k), executive summary 793 words.
- consistency_review: 12 contradictions, **5 high** (previous full runs: 7 high), 6 medium, 1 low.
  Its summary: the main structure is coherent (Month 12 go/no-go, the four gate criteria, the
  one-deferral rule, Dunkirk core with satellites); "contradictions appear where the later review,
  premortem and self-audit documents follow older assumptions instead of the canonical facts".
  Executive summary and project plan side with the canonical facts.
- Remaining work: the late critique stages (review_plan, premortem, self_audit; Haiku without
  thinking) still adopt values from the pre-reconciliation assumptions. Options: give them the
  assumptions with a "superseded where canonical facts differ" label, or move premortem to tier mid.

### Full run: gibraltar_tunnel (`runs/gibraltar`, 2026-10-06)

Baseline prompt and plan date (2026-09-05); assumptions explicitly superseded by canonical facts;
compiler-style diagnostics in consistency_review.
- 73/73 stages, 0 failures, 213 LLM calls, 11 web searches, **1h20m**; 42 canonical facts;
  report 161k words; executive summary 806 words (baseline 1,969).
- Structure vs baseline: 3 flags, all content-derived (lever names as keys; "## Location 1" heading
  in the shortened assumptions; an assumptions-derived risk heading in report.md).
- consistency_review: 12 contradictions, 6 high / 6 medium. Its summary: the core spine (EUR 40bn
  cap = 34bn base + 6bn contingency, phase tranches 2.5+4.5+15+12 = 34, the Month 12/18/24/30/36/72/180
  milestones, the hybrid concept) is consistent across executive summary, project plan and pitch;
  calendar arithmetic checks out. Every diagnostic names its offending document: premortem (6),
  review_plan (3), self_audit (3), pitch (2), executive summary (1).
- Conclusion: the reconciled facts now hold in the documents written directly from them; the late
  critique stages (premortem, review_plan, self_audit; Haiku, no thinking, long chained prompts) are
  where violations concentrate. Candidate fixes: tier mid for premortem (3 calls), or a repair pass
  that regenerates only the documents named by HIGH diagnostics, with the diagnostics as input.

### Enforcement: repair loop + premortem on Sonnet (2026-10-06)

Following Codex ("0 HIGH -> publish; 1+ HIGH -> regenerate offending sections; still HIGH -> publish
only with FAILED CONSISTENCY status"):
- `consistency_review` (lint pass 1) -> new `consistency_repair` -> new `consistency_recheck` (lint
  pass 2) -> report. The repair asks Sonnet, per document named in a HIGH/MEDIUM diagnostic, for exact
  find/replace edits (verbatim excerpt -> corrected text); Python applies them, so unrelated text stays
  verbatim and nothing is re-typed. Repaired copies (`repaired_*.md`) of the 7 reader-facing documents
  feed the report; PlanExe's original files are untouched. Remaining HIGH items after pass 2 show a
  "Consistency lint FAILED" banner. Shared review prompt/schema: `planexe_skill/shared/consistency/`.
- premortem moved to tier mid (Sonnet, low effort); it was the most frequent offender (6 of 12).
- Tested on a copy of the Gibraltar run (lint 1 from the full run; 6 LLM calls, 3m47s): 48 edits
  applied to executive summary, pitch, review plan, premortem and self-audit, 0 failed to match;
  high-severity contradictions 6 -> 2 (medium 6 -> 10: pass 2 also finds new, smaller issues).
  The premortem-on-Sonnet change is not yet validated in a full run.

### Codex comparison of the Gibraltar run with the 2025 baseline

Codex: **8.4/10 vs 6.6/10** ("beginning to look like a planning engine rather than a report
generator"; ~25-30% better planning quality, 50%+ better decision usefulness and epistemic discipline).
Biggest gains: falsifiable gates with "If NO" consequences, numbers with provenance (canonical facts),
the consistency/repair loop. Remaining weaknesses, both addressed at the source:
- **Economics not one closed model** (demand -> revenue -> opex -> debt service -> subsidy) and the
  fallback presented as fitting the EUR 40B cap. canonical_facts must now close that chain with the
  arithmetic in `basis`, state any funding gap, and say whether each fallback fits the cap/deadline.
  Re-generated on the Gibraltar copy (1 call): 4.5M pax x EUR 100 = EUR 450M + EUR 100M ancillary;
  opex EUR 75M; EUR 8B debt -> EUR 346M/yr service, DSCR 1.37x (1.11x at -20% demand, below the 1.2x
  threshold); EUR 32B non-repayable sponsor capital stated as the gap; fallback +EUR 5-15B exceeds the
  cap by up to EUR 9B and needs a new funding decision.
- **Information density for casual readers.** The report now opens with a short "Decision Dashboard"
  (decision kernel + consistency summary); the full Consistency Check and Canonical Facts sections move
  to the analysis part of the report.

### Full run: delhi_water (`runs/delhi`, 2026-10-06)

First full run with the complete pipeline (canonical facts incl. economic chain, premortem on Sonnet,
repair loop, Decision Dashboard). Baseline prompt and plan date (2026-09-06).
- 75/75 stages, 0 failures, 208 LLM calls, 14 web searches, **57 minutes** (fastest full run so far).
- Consistency: lint pass 1 found 5 high / 7 medium; 49 repair edits applied (0 missed); pass 2 still
  4 high / 8 medium -> report carries the FAILED banner (hub-plant retention vs debt-service economics,
  early spend before the first tranche, idle-factory carrying cost, fallback vs kill dates).
- vs baseline: the baseline picks the "Pragmatic Foundation" and summarizes in 240 words ("secure $250M
  green bond funding ... 5,000 m3/day ... 80% community acceptance"), without an economic model. The new
  plan has a 6-question decision kernel (concessional first tranche, four-agency protocol, concentrate
  disposal route, DJB multi-plant framework incl. hub-plant retention, Gate 1 at Month 12 with >=5 binding
  units, Gate 2 treatment-train performance) and a closed economic chain that exposes the core problem:
  USD 0.80/m3 service tariff x 16.67M m3 = USD 13.3M revenue, opex USD 8.3M, debt service USD 7.4M ->
  DSCR 0.68x, a USD 2.4M/yr shortfall that module sales must cover; fallbacks are costed against the cap
  (on-site ZLD would consume 36-67% of contingency; a 12-month DJB delay strands USD 50-80M of capex).
- Weaknesses: length (visible report text ~120k words vs ~31k; executive summary 805 vs 240 words) and
  4 remaining high-severity contradictions.

## Results

See `verify/results/SUMMARY.md` (regenerate with `python3 -m verify.summary`); raw judge
transcripts are in `verify/results/<stage>.json`.

| stage | tier | gibraltar | datacenter | rail | heatwave |
|---|---|---|---|---|---|
| screen_planning_prompt | high | win 8.0/7.0 | tie 7.0/7.0 | win 8.0/7.0 | win 7.5/6.0 |
| setup | low | identical | identical | identical | identical |
| extract_constraints | high | win 6.5/5.5 | win 8.5/5.0 | win 7.5/6.0 | win 9.0/4.0 |
| identify_purpose | high | win 8.0/6.0 | win 8.0/6.0 | win 8.0/5.5 | win 7.5/5.0 |
| premise_attack | high | win 8.0/3.5 | win 8.5/3.5 | win 8.5/3.0 | win 9.0/3.0 |
| redline_gate | high | win 6.5/5.5 | win 9.0/4.0 | win 8.0/7.0 | win 7.5/7.0 |
| classify_domain | high | win 7.0/5.0 | win 7.0/5.0 | win 7.0/4.5 | win 8.0/3.0 |
| plan_type | high | win 8.0/7.0 | win 8.0/7.5 | win 8.0/5.0 | win 8.0/7.0 |
| potential_levers | high | win 9.0/4.0 | win 9.0/4.0 | win 9.0/4.0 | win 9.0/4.0 |
| potential_levers_constraint | high | win 8.0/6.0 | win 8.5/2.0 | win 7.5/4.0 | win 8.0/5.0 |
| triage_levers | high | win 6.5/6.0 | win 7.5/5.0 | win 8.0/6.0 | win 7.0/5.5 |
| enrich_levers | high | win 8.0/5.5 | win 8.0/5.0 | win 8.0/4.0 | win 8.0/5.0 |
| triaged_levers_constraint | high | win 7.0/6.0 | win 8.0/5.0 | win 8.0/5.0 | win 8.0/5.0 |
| enriched_levers_constraint | high | LOSS 7.0/7.5 | win 8.0/4.5 | win 7.0/4.5 | win 7.0/5.0 |
| focus_on_vital_few_levers | high | LOSS 5.0/8.0 | win 8.5/3.0 | win 8.0/4.5 | win 8.0/5.0 |
| candidate_scenarios | high | win 7.0/6.0 | win 7.0/5.0 | win 7.5/5.0 | win 7.0/4.5 |
| strategic_decisions_markdown | low | identical | identical | identical | identical |
| vital_few_levers_constraint | high | win 7.5/6.0 | win 8.0/4.0 | win 6.5/4.5 | win 8.0/5.0 |
| candidate_scenarios_constraint | high | win 6.5/6.0 | win 7.0/4.5 | win 8.0/4.0 | win 7.0/4.5 |
| select_scenario | high | win 8.0/6.0 | win 9.0/4.0 | win 8.0/6.0 | win 8.5/6.0 |
| scenarios_markdown | low | identical | identical | identical | identical |
| selected_scenario_constraint | high | win 7.5/6.5 | win 7.5/4.5 | win 8.0/3.5 | win 8.0/5.5 |
| physical_locations | low | tie 6.5/6.5 | win 6.0/5.0 | win 7.5/4.5 | LOSS 4.5/5.0 |
| currency_strategy | low | win 7.5/5.5 | win 7.5/5.0 | win 8.0/3.0 | LOSS 5.0/7.5 |
| identify_risks | low | tie 6.5/6.5 | win 7.0/4.5 | win 7.5/5.0 | win 6.5/4.5 |
| make_assumptions | low | win 7.0/6.0 | win 7.0/4.0 | win 7.0/4.5 | win 7.0/4.5 |
| distill_assumptions | low | win 7.5/5.0 | win 7.0/4.5 | win 7.0/4.5 | win 8.0/4.0 |
| review_assumptions | low | LOSS 5.5/7.0 | win 6.0/5.0 | tie 5.0/6.0 | win 6.5/4.5 |
| consolidate_assumptions_markdown | low | tie 7.0/7.0, tie 6.0/5.5 | tie 7.0/7.0, win 6.5/5.0 | tie 6.0/6.0, tie 5.5/6.0 | tie 6.0/6.0, tie 5.5/5.5 |
| pre_project_assessment | low | win 7.0/5.5 | win 7.0/4.0 | tie 5.5/6.0 | win 7.0/4.5 |
| project_plan | low | win 8.0/5.5 | win 7.0/3.5 | win 7.5/4.0 | win 7.5/4.0 |
| create_wbs_level1 | low | LOSS 5.5/8.0 | tie 6.0/5.0 | tie 6.0/6.5 | win 6.0/4.5 |
| governance_phase1_audit | low | win 8.0/5.0 | win 7.5/5.5 | win 8.0/5.5 | win 8.0/5.0 |
| related_resources | mid | win 8.0/2.5 | win 8.0/2.0 | win 8.0/3.0 | win 8.0/3.0 |
| find_team_members | low | LOSS 5.0/8.0 | win 7.0/5.0 | win 7.0/6.0 | tie 6.5/6.5 |
| governance_phase2_bodies | low | LOSS 5.5/7.5 | win 8.0/5.0 | win 7.5/5.0 | win 7.0/4.5 |
| swot_analysis | mid | win 8.0/5.0 | win 8.0/5.0 | win 8.0/4.0 | win 8.5/4.5 |
| enrich_team_members_with_contract_type | low | LOSS 5.0/7.0 | win 6.5/5.0 | win 7.0/5.5 | tie 6.0/5.5 |
| expert_review | low | LOSS 5.5/7.0 | win 7.0/3.0 | win 8.0/4.0 | win 7.5/5.0 |
| governance_phase3_impl_plan | low | tie 6.5/6.5 | win 7.0/4.5 | win 6.5/5.0 | win 7.0/4.5 |
| enrich_team_members_with_background_story | low | tie 6.0/6.5 | win 8.0/1.0 ⚠2 | win 7.0/5.5 | win 8.0/4.0 |
| governance_phase4_decision_escalation_matrix | low | win 8.0/5.5 | win 8.0/4.5 | win 7.0/5.5 | win 7.5/4.5 |
| enrich_team_members_with_environment_info | low | win 7.5/6.0 | tie 5.5/5.5 | win 7.0/4.5 | win 7.0/5.0 |
| governance_phase5_monitoring_progress | low | win 8.0/6.0 | win 7.5/4.5 | win 8.0/4.5 | win 8.0/5.0 |
| governance_phase6_extra | low | win 7.5/5.5 | win 7.5/5.5 | win 7.5/5.5 | win 8.0/6.0 |
| review_team | low | LOSS 5.5/7.5 | win 7.0/5.5 | win 7.5/5.0 | win 7.0/4.5 |
| consolidate_governance | low | identical | identical | identical | identical |
| team_markdown | low | identical | identical | identical | identical |
| data_collection | low | win 7.5/5.0 | win 7.0/4.5 | win 7.5/4.0 | win 7.0/4.5 |
| identify_documents | low | LOSS 5.5/7.5 | win 7.0/5.0 | win 7.5/5.5 | win 7.0/4.5 |
| create_wbs_level2 | low | win 7.0/6.0 | win 7.0/4.0 | win 7.5/3.0 | win 7.0/4.0 |
| filter_documents_to_create | mid | win 8.0/6.0 | win 8.0/6.0 | win 8.0/5.5 | win 7.5/5.5 |
| filter_documents_to_find | low | tie 5.0/6.5 | win 6.5/5.5 | LOSS 5.0/6.0 | win 7.5/5.0 |
| draft_documents_to_create | low | tie 6.0/6.0 | win 7.0/5.0 | win 7.0/5.0 | win 7.0/4.5 |
| draft_documents_to_find | low | win 7.0/4.5 | win 7.5/5.0 | win 7.0/5.0 | win 7.0/4.5 |
| identify_task_dependencies | low | win 7.0/5.0 | win 7.0/4.5 | win 8.0/3.0 | LOSS 4.0/6.0 |
| wbs_project_level1_and_level2 | low | identical | identical | identical | identical |
| create_pitch | low | tie 6.0/6.5 | LOSS 3.5/6.0 | win 7.0/4.5 | win 7.0/5.0 |
| estimate_task_durations | low | LOSS 5.0/7.5 | win 7.0/5.5 | win 7.0/5.5 | win 6.5/5.5 |
| markdown_with_documents_to_create_and_find | low | identical | identical | identical | identical |
| convert_pitch_to_markdown | low | win 9.0/3.0 | LOSS 5.0/6.0 | win 8.0/6.0 | win 6.5/5.0 |
| create_wbs_level3 | low | win 7.0/5.5 | tie 6.5/5.5 | tie 6.5/5.5 | win 7.5/5.0 |
| wbs_project_level1_and_level2_and_level3 | low | identical | identical | identical | identical |
| create_schedule | low | identical | identical | identical | identical |
| review_plan | low | win 7.0/5.0 | tie 6.0/6.5 | win 6.5/5.5 | tie 5.5/5.5 |
| executive_summary | low | LOSS 6.0/6.5 | win 6.5/4.5 | win 6.5/4.5 | win 6.0/5.0 |
| questions_and_answers | low | win 7.0/7.0 | win 7.0/4.0 | win 7.0/4.0 | win 7.0/4.5 |
| premortem | low | win 7.5/6.0 | win 8.0/3.0 | win 8.0/2.0 | win 7.0/5.5 |
| prompt_adherence | low | win 8.0/3.5 | win 7.5/5.5 | win 7.0/5.0 | tie 5.5/5.5 |
| self_audit | low | win 8.0/6.0 | win 7.0/4.0 | win 7.0/4.0 | win 7.0/3.0 |
| report | low | identical | identical | identical | differs |

Cells: verdict of the blind A/B judge (position-swapped, 2 runs) and mean scores new/baseline (1-10); ⚠n = structural differences vs baseline; deterministic stages are compared byte-for-byte.
