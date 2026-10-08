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

## Getting started

You need:

- **Python 3.11 or newer** (standard library only; nothing to `pip install`).
- **The Claude Code CLI, logged in**: `claude auth login`. PlanExe2 makes its LLM calls through it, on
  your Claude subscription.
- **Usage budget**: a full plan is about 220-260 LLM calls and takes roughly 65-90 minutes.

### Recommended: clone the repo and ask your coding agent

```bash
git clone https://github.com/PlanExeOrg/PlanExe2.git
cd PlanExe2
claude
```

Then ask for a plan, e.g. "make a plan for a bakery in Lyon". The `make-plan` skill
(`.claude/skills/make-plan/`) takes over: it asks a few questions, drafts a 300-800 word prompt, checks it
with `check-prompt`, and launches only after you confirm. Codex and other agents follow the same steps via
`AGENTS.md`.

Plans are written to `runs/<name>/` inside the clone (ignored by git); the result is
`runs/<name>/report.html`. Update with `git pull`; each report's Metadata section names the PlanExe2 version
that produced it (`git describe`, e.g. `v2.0.2`).

### Without git: let the agent fetch it

In any Claude Code session, paste:

> Clone https://github.com/PlanExeOrg/PlanExe2, read its CLAUDE.md, and use its make-plan skill to make
> me a plan for a bakery in Lyon.

This works, but a session started outside the repo does not load the repo's skill on its own, so the
agent has to find and read `CLAUDE.md` first. Cloning and starting the agent inside the repo (above) is
more reliable.

### By hand

```bash
python3 -m planexe_skill check-prompt --prompt-file my_prompt.txt   # optional: is the prompt usable?
python3 -m planexe_skill create runs/my_plan --prompt-file my_prompt.txt [--start-date YYYY-MM-DD]
python3 -m planexe_skill run runs/my_plan                    # resumable; prints progress with an ETA
```

The prompt is flowing prose: objective, scope, location, budget, timeline, stakeholders, constraints and
success criteria. The start date (Month 0) defaults to today and may be in the past or the future.

> Running inside a sandboxed agent (e.g. Claude Code desktop with sandbox on)? The child
> `claude` process needs keychain access for auth, so run the command outside the sandbox.

### Why there is no pip package

There are no dependencies to install, and the skills, prompts and schemas live in the repo next to the
agent instructions that drive them. A pip package would move the `make-plan` skill out of the user's
project and need a separate install step for the guided flow. A Claude Code plugin (bundling `make-plan`
and the runner, installed with `/plugin install`) is the likely route if PlanExe2 should work from any
folder without cloning.

## What the report contains

The report leads with the decisions and key facts, not the workshop:

1. **Key decisions and facts**: the Decision Dashboard (the go/no-go gates), **Decisions
   Required** (each open decision with options, downstream consequences, owner and decide-by month, plus
   the strategic choices the generator made on your behalf, to ratify), the Canonical Facts (the numbers
   and dates every section must use), the Executive Summary and the Gantt.
2. **Supporting analysis**: PlanExe's planning documents (pitch, project plan, assumptions,
   governance, SWOT, team, expert criticism, WBS, premortem, ...).
3. **Audit trail**: **Validation Status** (what "validated" means here: which sections searched the web,
   the consistency lint before and after repair, a deterministic re-computation of every written
   calculation, and which sections were not checked), the full consistency check, prompt vetting, prompt
   adherence and metadata (generator version, commit, models per stage).

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

## Versioning and report metadata

Every report's Metadata section names its generator version (`git describe`: `v2.0.0` on the tag,
`v2.0.0-3-gabc1234` three commits later, `+modified` for uncommitted changes), repo and commit. A run can mix code versions
(resumed runs, stages regenerated after an edit), so this is kept per stage:
`RUN_DIR/planexe_report_metadata.json` lists, for every stage, the generator version and commit, when it
ran, which models it used, how many LLM calls and web searches it made, plus hand-edited intermediary
files and adopted stages; the report's last section, "Metadata", renders it (runs made before
2026-10-07 have `planexe_provenance.json`, which the next `run` replaces). Each `*_raw.json` also carries `metadata.generator`
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
