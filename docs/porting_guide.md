# Porting a PlanExe stage to a skill

Read this before porting. Look at the already-ported skills in `skills/` (e.g.
`identify_purpose`, `premise_attack`, `classify_domain`) for the conventions in practice.

## Sources

- Stage list, inputs/outputs and PlanExe source files per stage:
  `docs/reference/planexe_pipeline_dag.json` (node `id` = skill name).
- PlanExe repo: `~/git/PlanExeGroup/PlanExe/worker_plan/` — node wrapper in
  `worker_plan_internal/plan/nodes/<file>.py` (what files are read, how the user prompt is
  assembled), business logic in the module listed under `source_files`.
- Baseline outputs (what the files must look like):
  `.verify_work/baselines/<baseline>/` (extracted from `~/git/PlanExe-web/*.zip`; run
  `python3 -m verify.eval_stage <stage> --no-judge` once to extract them if missing).

## Extract prompts and schemas verbatim

```bash
cd ~/git/PlanExeGroup/PlanExe/worker_plan
.venv/bin/python ~/git/PlanExeGroup/PlanExe2/tools/extract_planexe_module.py worker_plan_internal.<pkg>.<module> /tmp/x
```

This writes every pydantic model's JSON schema and every `*PROMPT*` string constant. Prompts
assembled at runtime (f-strings, concatenations, per-purpose variants) must be reproduced in
`run.py` or dumped via a small snippet in that venv. Copy prompts into `skills/<stage>/prompts/`
and schemas into `skills/<stage>/schema*.json` — keep the text verbatim unless a tweak is needed
(document every tweak, see below).

The PlanExe venv is ONLY a porting aid. Skills must be pure Python stdlib (no pydantic, no
llama_index, no pandas, no jinja). Import only from `planexe_skill.*` and the stdlib.

## Skill folder

```
skills/<stage>/
  SKILL.md      frontmatter + short description of the algorithm (what a human/agent needs to know)
  prompts/*.md  system prompts
  schema*.json  JSON schemas for structured output
  run.py        def run(ctx): ...
```

Frontmatter keys:

```yaml
---
name: <stage>                # == folder name == node id in planexe_pipeline_dag.json
description: one line
inputs: [file, ...]          # EXACTLY the files the PlanExe node reads (filenames, not stages)
outputs: [file, ..., pattern_{n}_raw.json]   # the node's outputs; fan-out files use {n}
tier: high | low             # high = Sonnet+high effort; low = Haiku
est_llm_calls: N             # typical number of LLM calls (used for the ETA)
parallel_llm: K              # optional: how many of those calls run concurrently
uses: [planexe_skill/shared/x.py]   # optional: shared helper modules imported by run.py
---
```

The runner enforces the contract: reading a file not listed in `inputs` or writing one not in
`outputs` raises. Every fixed output must be written. Fan-out output patterns must be listed
(e.g. `draft_documents_to_find_{n}_raw.json`).

## ctx API (planexe_skill/context.py)

- `ctx.read_text(name)`, `ctx.read_json(name)`, `ctx.write_text(name, s)`, `ctx.write_json(name, obj)`
- `ctx.skill_file("prompts/system.md")`, `ctx.skill_json("schema.json")`
- `ctx.llm(system=, user=, schema=, tier=None, label="") -> LLMResult(data, text, metadata)`
- `ctx.map(fn, items)` — run independent work in threads (LLM concurrency stays bounded globally)
- `ctx.log(msg)` — goes to `RUN_DIR/.planexe_skill/logs/<stage>.log`

Helpers in `planexe_skill/planexe.py`:
- `structured(ctx, system, user, schema, tier=None, label="") -> (dict, LLMResult)`
- `raw_document(response, result, system_prompt, user_prompt)` — PlanExe's common raw layout
- `planexe_metadata(result)` — the `metadata` dict PlanExe writes
- `format_json_for_query(obj)` — PlanExe's `format_json_for_use_in_query`

Shared logic for a family of stages (e.g. the 5 constraint-checker stages, the governance
phases) goes in `planexe_skill/shared/<family>.py`; each skill using it lists it in `uses:`.

## Fidelity rules

- Same output filenames, same JSON structure (keys, nesting, value types), same markdown
  structure (headings/sections) as the baseline. Compare with the baseline files.
- Port the deterministic code faithfully (markdown rendering, cleanup, dedupe, sorting, IDs,
  CSV/HTML generation). Deterministic stages must be byte-identical to the baseline given the
  baseline inputs.
- Multi-call loops (batches, per-item calls, chat-history follow-ups): keep the same number and
  shape of calls. PlanExe passes chat history for follow-up calls; `ctx.llm` is single-turn, so
  embed prior turns in the user message (e.g. a "## Previous responses" section) — keep the
  information the model saw equivalent. Independent per-item calls may run via `ctx.map`.
- PlanExe often swallows per-item failures and continues; mirror that.
- `pydantic.model_dump()` fills defaults for optional fields — make sure missing optional keys
  are present (as null/default) in the raw output so the JSON shape matches.
- Don't hardcode anything specific to one plan. Skills are general purpose.

## Verify

LLM calls go through `claude -p`, which needs keychain access: run verification commands with
the Bash sandbox disabled.

```bash
python3 -m verify.eval_stage <stage> [<stage> ...]          # run + structure + judge on 4 baselines
python3 -m verify.eval_stage <stage> --no-judge             # just run + structure
python3 -m verify.eval_stage <stage> --reuse                # re-judge existing outputs
```

Pass = structure OK on all 4 baselines and win/tie on >= 3/4 (deterministic: identical).
On a loss, read the judge analyses in `verify/results/<stage>.json` and the outputs in
`.verify_work/stage_runs/<stage>/<baseline>/`, find the cause, fix, re-run. Typical causes: a
schema description that conflicts with the system prompt, a lost piece of context in the user
prompt, truncation, Haiku being too terse for a stage that needs depth (consider tier high).

## Document

For every stage, write a row for `report.md`: verbatim port / what changed and why, and any
regression found + fix. Don't edit `report.md` concurrently with other agents — return the
rows in your final message instead.
