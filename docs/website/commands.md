---
title: Commands
---

# Commands

The [recommended way](getting_started.md) is to let your coding agent run these. This page is for running
PlanExe2 by hand, and for reference. All commands run from the repo root.

## By hand

```bash
python3 -m planexe_skill check-prompt --prompt-file my_prompt.txt
python3 -m planexe_skill create runs/my_plan --prompt-file my_prompt.txt
python3 -m planexe_skill run runs/20261008_my_plan
```

**The prompt** is flowing prose, typically 300-800 words, not bullet lists or headings. Cover the objective,
scope, location, budget, timeline, scale, stakeholders, constraints and success criteria. Label guesses as
assumptions. `check-prompt` (one LLM call) rates each of these as present, partial or missing, suggests
questions, and exits with 0 when the prompt is ready.

**`create`** names the run directory after the date it is created: `runs/my_plan` becomes
`runs/20261008_my_plan`, and the path is printed. A name that already starts with `yyyymmdd_` is kept;
`--no-date-prefix` uses the path as given. `--start-date YYYY-MM-DD` sets the plan's Month 0 (default
today; past and future dates are fine).

**`run`** runs every stage that needs running and resumes where it left off.

## Command reference

| command | what it does |
|---|---|
| `check-prompt --prompt-file F` | pre-flight check of a prompt (1 LLM call): usability, completeness, questions |
| `create RUN_DIR --prompt-file F [--start-date D]` | create a run dir (`plan_raw.json`, `start_time.json`); D = Month 0 |
| `run RUN_DIR` | run every dirty stage; resumes where it left off |
| `run RUN_DIR --only STAGE` | run one stage (its inputs must already exist) |
| `run RUN_DIR --until STAGE` | run a stage and everything it depends on |
| `run RUN_DIR --force STAGE` | re-run a stage even if it is clean |
| `run RUN_DIR --force-downstream STAGE` | regenerate a stage and everything after it |
| `run RUN_DIR --dry-run` | list stages that would run |
| `status RUN_DIR` | which stages are dirty and why |
| `explain RUN_DIR STAGE` | details for one stage |
| `graph [--dot]` | stages in topological order |

`create` and `run` also accept `--prompt TEXT` instead of a file, and `--plan-raw FILE` to copy an existing
`plan_raw.json` (keeping its date).

### Options for `run`

| option | default | |
|---|---|---|
| `--workers N` | 4 | concurrent LLM calls |
| `--model-high M` | `claude-sonnet-5-5` | model for `tier: high` stages |
| `--model-mid M` | `claude-sonnet-5-5` | model for `tier: mid` stages |
| `--model-low M` | `claude-haiku-4-5-20251001` | model for `tier: low` stages |

## Progress, logs and stopping

- Progress is printed with an ETA and mirrored to `RUN_DIR/.planexe_skill/progress.json`.
- Per-stage logs, with every prompt and response, are in `RUN_DIR/.planexe_skill/logs/`.
- To stop gracefully, create the file `RUN_DIR/.planexe_skill/stop`.

## Failures and resuming

LLM calls stream their output. A call that produces nothing for 90 seconds is killed and retried once, and
no call may run longer than 10 minutes. Completed LLM calls inside a stage are cached, so re-running after a
failure only repeats the calls that didn't finish.

On failure the runner prints the failing stage, the error, the log path and a retry command. To resume, run
`python3 -m planexe_skill run RUN_DIR` again.

The child `claude` process needs keychain access, so run outside any sandbox. If authentication fails, run
`claude auth login` and resume.

## Versioning and report metadata

Every report's Metadata section names its generator version (`git describe`: `v2.0.0` on the tag,
`v2.0.0-3-gabc1234` three commits later, `+modified` for uncommitted changes), repo and commit.

A run can mix code versions (resumed runs, stages regenerated after an edit), so this is recorded per stage
in `RUN_DIR/planexe_report_metadata.json`: generator version and commit, when it ran, which models it used,
how many LLM calls and web searches it made, plus hand-edited intermediary files and adopted stages. Each
`*_raw.json` also carries `metadata.generator` (repo, commit, git tag).

The plan's start date (Month 0, `start_time.json`) is independent of when the plan is generated, so plans can
be dated in the past or the future.
