# PlanExe2

> **PlanExe v1:** generate an unusually comprehensive expert planning workshop.
> **PlanExe2:** construct a partially validated model of the project, then expose what humans still have to decide.

Formerly PlanExe-skill.
[PlanExe](https://github.com/PlanExeOrg/PlanExe)'s plan-generation pipeline, rewritten as
**skills** executed by a tiny, dependency-free Python DAG runner.

- No pip install. Python >= 3.11 standard library only.
- LLM calls go through the headless Claude Code CLI (`claude -p`), using your Claude subscription.
- Every stage writes the same intermediary files as PlanExe (same names, same JSON/markdown structure).
- Edit any intermediary file and re-run: your edit is kept and everything downstream is regenerated.
- Progress bar with an ETA based on the DAG's critical path.

## Quick start

With a coding agent: open this repo in Claude Code and ask for a plan ("make a plan for a bakery in
Lyon"). The `make-plan` skill asks a few questions, drafts and checks the prompt, and launches only after
you confirm. By hand:

```bash
claude auth login                      # once
python3 -m planexe_skill create runs/my_plan --prompt-file my_prompt.txt
python3 -m planexe_skill run runs/my_plan
```

A full plan is ~180-250 LLM calls and takes roughly 15-45 minutes. The final report is
`runs/my_plan/report.html`.

> Running inside a sandboxed agent (e.g. Claude Code desktop with sandbox on)? The child
> `claude` process needs keychain access for auth, so run the command outside the sandbox.

## What the report contains

The report leads with the model, not the workshop:

1. **The model and what you must decide**: the Decision Dashboard (the go/no-go gates), **Decisions
   Required** (each open decision with options, downstream consequences, owner and decide-by month, plus
   the strategic choices the generator made on your behalf, to ratify), the Canonical Facts (the numbers
   and dates every section must use), **Validation Status** (what "validated" means here: which stages
   searched the web, the consistency lint before and after repair, a deterministic re-computation of
   every written calculation, and which sections are unchecked model output), the Executive Summary and
   the Gantt.
2. **Supporting analysis**: PlanExe's planning documents (pitch, project plan, assumptions,
   governance, SWOT, team, expert criticism, WBS, premortem, ...).
3. **Audit trail**: the full consistency check, prompt vetting, prompt adherence and provenance.

## Commands

| command | what it does |
|---|---|
| `check-prompt --prompt-file F` | pre-flight check of a prompt (1 LLM call): usability, completeness, questions |
| `create RUN_DIR --prompt-file F [--start-date D]` | create a run dir (`plan_raw.json`, `start_time.json`); D = Month 0 |
| `run RUN_DIR` | run every dirty stage; resumes where it left off |
| `run RUN_DIR --only STAGE` | run one stage (its inputs must already exist) |
| `run RUN_DIR --until STAGE` | run a stage and everything it depends on |
| `run RUN_DIR --force-downstream STAGE` | regenerate a stage and everything after it |
| `run RUN_DIR --dry-run` | list stages that would run |
| `status RUN_DIR` | which stages are dirty and why |
| `explain RUN_DIR STAGE` | details for one stage |
| `graph [--dot]` | stages in topological order |

Options: `--workers N` (concurrent LLM calls, default 4), `--model-high`, `--model-low`.
Create `RUN_DIR/.planexe_skill/stop` to stop gracefully; progress is mirrored to
`RUN_DIR/.planexe_skill/progress.json`, per-stage logs (every prompt and response) live in
`RUN_DIR/.planexe_skill/logs/`.

## Versioning and provenance

Every report names its generator under the title: **PlanExe2 + version** (`git describe`: `v2.0.0` on the tag,
`v2.0.0-3-gabc1234` three commits later, `+modified` for uncommitted changes) and the repo/commit. A run can
mix code versions (resumed runs, stages regenerated after an edit), so provenance is kept per stage:
`RUN_DIR/planexe_provenance.json` lists, for every stage, the generator version and commit, when it ran,
which models it used and how many LLM calls it made, plus hand-edited intermediary files and adopted
stages; the report's last section renders it. Each `*_raw.json` also carries `metadata.generator`
(repo, commit, git tag). The plan's start date (Month 0, `start_time.json`) is independent of when the
plan is generated, so plans can be dated in the past or the future.

To release a version: `git tag v2.0.0 && git push --tags`.

## Failures and resuming

LLM calls stream their output; a call that produces nothing for 90 s is killed and retried once,
and no call may run longer than 10 minutes. Completed LLM calls inside a stage are cached, so
re-running after a failure only repeats the calls that didn't finish.

## How dirtiness works

`RUN_DIR/.planexe_skill/manifest.json` stores, for every stage, hashes of its skill folder,
its input files and its output files. A stage re-runs when an output is missing, its skill
folder changed, or one of its inputs changed. Hand-edited outputs are kept and make the
downstream stages dirty. Output files without a manifest record are adopted as clean, so you
can drop a PlanExe run's files into a run dir and regenerate selected stages.

## Skills

Each stage is a folder in `skills/`:

```
skills/identify_purpose/
  SKILL.md        frontmatter (inputs, outputs, tier, est_llm_calls) + description
  prompts/        system prompts, verbatim from PlanExe unless noted in report.md
  schema.json     JSON schema for structured output
  run.py          def run(ctx): reads inputs, calls ctx.llm(...), writes outputs
```

`tier: high` stages (the foundational early stages) use Sonnet with high effort,
`tier: low` stages use Haiku. Edges in the DAG are derived from file names: a stage depends
on whichever stage produces one of its inputs.

Stages added by PlanExe2 (not in PlanExe v1): `canonical_facts` (one table of key numbers and dates,
before the project plan), `consistency_review` and `consistency_repair` (lint the core documents against
the canonical facts and repair them with exact edits, including deterministic arithmetic fixes),
`decision_register` (the open decisions as options/consequences/owner/deadline, and the choices to
ratify) and `arithmetic_check` (deterministic re-computation of every written calculation).

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

Verification against PlanExe baselines lives in `verify/`; findings are in `report.md`.
