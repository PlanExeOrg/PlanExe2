---
title: Getting started
---

# Getting started

## Requirements

- **Python 3.11 or newer**. Standard library only; nothing to `pip install`.
- **The Claude Code CLI, logged in**: `claude auth login`. PlanExe2 makes its LLM calls through it, on your
  Claude subscription.
- **Usage budget**: a full plan is about 220-260 LLM calls and takes roughly 65-90 minutes.

## Recommended: clone the repo and ask your coding agent

```bash
git clone https://github.com/PlanExeOrg/PlanExe2.git
cd PlanExe2
claude
```

Then ask for a plan, for example "make a plan for a bakery in Lyon". Codex and other agents follow the same
steps via `AGENTS.md`.

### What the agent does

The `make-plan` skill (`.claude/skills/make-plan/`) takes over:

1. **Asks a few questions** about what the plan needs and you haven't said yet: objective, location,
   budget, timeline, scale, stakeholders, constraints, success criteria. Each question comes with suggested
   answers to pick from, and "you decide" where a sensible default exists. It also asks for the plan's start
   date (Month 0); past and future dates are fine.
2. **Drafts the prompt**: 300-800 words of prose built from your answers. Anything it assumed on your behalf
   is labelled as an assumption, so the plan treats it as an estimate.
3. **Checks the prompt** with `check-prompt` (one LLM call). If important items are missing, it asks again.
4. **Asks for confirmation.** It shows the prompt, the check result, the start date and the cost, and
   launches only after you say yes.
5. **Runs the plan in the background** and reports back when it is done, starting with the decisions you
   need to make.

### While it runs

Progress lines show the current stage and an ETA based on the DAG's critical path. The same data is in
`runs/<yyyymmdd>_<name>/.planexe_skill/progress.json`. If something fails, re-running resumes where it
stopped; finished stages and completed LLM calls are kept.

### The result

Plans are written to `runs/<yyyymmdd>_<name>/` inside the clone (ignored by git), for example
`runs/20261008_cross_border_rail_ticketing/`. Open `report.html`; `report.md` has the same content. See
[The report](report.md) for what is in it.

Update with `git pull`. Each report's Metadata section names the PlanExe2 version that produced it.

## Without git: let the agent fetch it

In any Claude Code session, paste:

> Clone https://github.com/PlanExeOrg/PlanExe2, read its CLAUDE.md, and use its make-plan skill to make
> me a plan for a bakery in Lyon.

This works, but a session started outside the repo does not load the repo's skill on its own, so the agent
has to find and read `CLAUDE.md` first. Cloning and starting the agent inside the repo is more reliable.

## Sandboxed agents

The child `claude` process needs keychain access for authentication. If your agent runs commands in a
sandbox (for example Claude Code desktop with sandbox on), the plan run must happen outside it. If
authentication fails, run `claude auth login` and resume.

## Why there is no pip package

There are no dependencies to install, and the skills, prompts and schemas live in the repo next to the agent
instructions that drive them. A pip package would move the `make-plan` skill out of your project and need a
separate install step for the guided flow. A Claude Code plugin is the likely route if PlanExe2 should work
from any folder without cloning.

## Next

- Run it without an agent: [Commands](commands.md).
- Understand what gets generated and why: [How it works](how_it_works.md).
