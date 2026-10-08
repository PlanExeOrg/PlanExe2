# PlanExe2

> **PlanExe v1:** generate an unusually comprehensive expert planning workshop.
> **PlanExe2:** construct a partially validated model of the project, then expose what humans still have to decide.

[PlanExe v1](https://github.com/PlanExeOrg/PlanExe)'s plan-generation pipeline, rewritten as
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

Plans are written to `runs/<yyyymmdd>_<name>/` inside the clone (ignored by git), e.g.
`runs/20261008_cross_border_rail_ticketing/`; the result is its `report.html`. Update with `git pull`; each report's Metadata section names the PlanExe2 version
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
python3 -m planexe_skill run runs/20261008_my_plan           # resumable; prints progress with an ETA
```

`create` names the run dir after the date it is created (`runs/my_plan` becomes `runs/20261008_my_plan`) and
prints the path; a name that already starts with `yyyymmdd_` is kept, and `--no-date-prefix` uses the path as
given. The prompt is flowing prose: objective, scope, location, budget, timeline, stakeholders, constraints and
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

## Documentation

Full documentation: [docs.planexe.org](https://docs.planexe.org)

- [Getting started](https://docs.planexe.org/getting_started/)
- [The report](https://docs.planexe.org/report/): what each section is for
- [Commands](https://docs.planexe.org/commands/): command reference, options, stopping, failures and
  resuming, versioning and report metadata
- [How it works](https://docs.planexe.org/how_it_works/): the DAG, skill folders, tiers, dirtiness, editing
  intermediary files, stages added by PlanExe2

The site is built from `docs/website/` by [PlanExe-docs](https://github.com/PlanExeOrg/PlanExe-docs).

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

Verification against PlanExe baselines lives in `verify/`; findings are in `report.md`.

## License

MIT, see [LICENSE](LICENSE). Includes code and prompts from [PlanExe v1](https://github.com/PlanExeOrg/PlanExe), also MIT.
