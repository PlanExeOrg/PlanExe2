# PlanExe-skill design

Date: 2026-10-04
Branch: `skill-lab1`

## Goal

Port PlanExe's Luigi pipeline (73 stages, see `docs/reference/planexe_pipeline_dag.json`)
into a dependency-free Python project where every stage is a *skill*, executed by a
lightweight DAG runner. A coding agent (Claude Code, later Codex) can be pointed at the
repo and generate a full PlanExe plan with one command.

Non-goals: `napkin_math/` (monte carlo), docker, databases, model switching via
llama_index, the `fast_but_skip_details` mode.

## Decisions (agreed with user)

| Topic | Decision |
|---|---|
| LLM backend | Headless agent CLI: `claude -p` (Codex backend later, behind same interface) |
| Models | tier `high` = Sonnet 5.5 + `--effort high` for the early, foundational stages (through `project_plan`); tier `low` = Haiku 4.5 for the rest. Overridable per run. |
| Skill format | `skills/<stage>/` folder: `SKILL.md` + `schema*.json` + `run.py` |
| Dirty rule | content-hash manifest |
| Dependencies | stdlib only, Python >= 3.11 |
| Parallelism | 4 workers |
| Detail mode | `all_details` only |
| Judging | structural diff + blind A/B LLM judge (position-swapped) |
| Checkpoints | fully autonomous; commit+push as work lands |

## Layout

```
planexe_skill/            runtime package (stdlib only)
  skill.py                parse SKILL.md frontmatter, load run.py
  dag.py                  build graph from skills (file producer map), topo sort, cycle check
  manifest.py             per-run-dir manifest of hashes, dirty detection
  runner.py               thread-pool executor, retries, failure isolation
  progress.py             progress bar + ETA, progress.json, timings history
  context.py              SkillContext passed to run.py (read/write/llm helpers)
  llm/base.py             Backend interface + LLMResult
  llm/claude_cli.py       `claude -p` backend with --json-schema
  llm/fake.py             deterministic fake backend for tests
  cli.py                  python -m planexe_skill run|status|explain|graph|new
skills/<stage>/
  SKILL.md                frontmatter (name, description, inputs, outputs, tier, est_llm_calls) + prose/prompt
  prompts/*.md / schema*.json   prompt text and JSON schemas used by run.py
  run.py                  def run(ctx): ...
verify/                   baseline tools: extract, structural diff, judge, per-task eval
tests/                    unittest suite (python -m unittest)
report.md                 findings, regressions, tweaks
```

## Skill contract

`SKILL.md` frontmatter (a small YAML subset parsed by our own parser: scalars and
lists of scalars):

```yaml
---
name: identify_purpose
description: Classify the plan as business, personal or other.
inputs: [plan.txt]
outputs: [identify_purpose_raw.json, identify_purpose.md]
tier: high
est_llm_calls: 1
---
```

Outputs may contain a `{n}` placeholder (`wbs_level3_{n}_raw.json`) for fan-out; the
manifest records the concrete files written. Inputs reference files, never stages: the
DAG derives edges by looking up which skill produces each input file. A file nobody
produces is a *root input* (only `plan.txt`-level seeds; the CLI provides them).

`run.py` exposes `run(ctx)`. `ctx` offers:

- `ctx.read_text(name)`, `ctx.read_json(name)`, `ctx.write_text(name, s)`, `ctx.write_json(name, obj)`
- `ctx.llm(system=..., user=..., schema=dict, tier=None) -> LLMResult` (parsed JSON, raw text, metadata)
- `ctx.skill_dir`, `ctx.run_dir`, `ctx.log(msg)`

Raw files mirror PlanExe's structure (same keys, `metadata` block filled with the
CLI model name, duration, byte count).

## DAG + dirty detection

`.planexe_skill/manifest.json` in the run dir records per stage: skill hash (hash of
its folder), input file hashes, output file hashes, completion time.

A stage needs to run when any of:
1. an output is missing (or for `{n}` outputs: no recorded files),
2. its skill hash differs from the recorded one,
3. an input's current hash differs from the recorded input hash.

If an output exists but has no manifest record, it is *adopted*: hashes recorded, stage
treated as clean. This makes it possible to seed a run dir from a baseline zip and
re-run one stage. User edits to an output are preserved (the stage is not re-run) and
make downstream stages dirty through rule 3. `--force STAGE` and `--force-downstream
STAGE` invalidate explicitly.

## Progress + ETA

Status line: `[ 23/73 stages | llm 41/~190 | 12m04s elapsed | ETA 21m | running: a, b ]`.
ETA = remaining estimated LLM calls × moving average seconds/call ÷ active workers,
seeded from `~/.planexe_skill/timings.json` (per-stage historical durations).
`run_dir/progress.json` mirrors the same data for agents to poll.

## Errors

A failed stage prints: stage name, input files, the exact command, stderr tail,
log path `run_dir/logs/<stage>.log`, and the command to rerun only that stage.
Independent stages keep running; dependents are marked `blocked`.

## Verification

Per stage, on 4 dev baselines (gibraltar_tunnel, datacenter_in_france,
cross_border_rail_ticketing, heatwave_resilience):
1. Copy the baseline into a temp run dir, delete only this stage's outputs.
2. Run this stage only (upstream = baseline files).
3. Structural check: same file set, JSON keys/types (recursively, list item shape),
   markdown heading outline.
4. Blind A/B judge (Sonnet), run twice with swapped order. Outcome per file:
   win / tie / loss.

Pass = structure matches and win-or-tie on >= 3/4 baselines. Losses are investigated
and the skill tweaked; tweaks are logged in `report.md`.

Final verification: full end-to-end runs from `plan.txt` of euro_adoption,
battery_breakthrough, gibraltar_tunnel and datacenter_in_france; every file judged
against baseline. Losing stages get fixed and the run resumes from there.
