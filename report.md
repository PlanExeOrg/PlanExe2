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

Cells: verdict of the blind A/B judge (position-swapped, 2 runs) and mean scores new/baseline (1-10); ⚠n = structural differences vs baseline; deterministic stages are compared byte-for-byte.
