---
title: PlanExe2
---

# PlanExe2

PlanExe2 turns a planning idea into a strategic plan draft: a single HTML report that leads with the
decisions you still have to make, backed by the supporting analysis and an audit trail of what was checked.

> **PlanExe v1:** generate an unusually comprehensive expert planning workshop.
>
> **PlanExe2:** construct a partially validated model of the project, then expose what humans still have to decide.

PlanExe2 is [PlanExe v1](https://github.com/PlanExeOrg/PlanExe)'s plan-generation pipeline, rewritten as
**skills** executed by a small, dependency-free Python DAG runner.

- No pip install. Python 3.11 or newer, standard library only.
- LLM calls go through the headless Claude Code CLI (`claude -p`), on your Claude subscription.
- You don't write the prompt yourself: your coding agent interviews you, drafts the prompt, checks it and
  launches only after you confirm.
- Every stage writes plain JSON and markdown files. Edit any of them and re-run: your edit is kept and
  everything downstream is regenerated.

The output is a draft to refine, not ground truth. It surfaces the questions and decisions a plan depends on.

## Pages

- [Getting started](getting_started.md): requirements and how to make your first plan.
- [The report](report.md): what the report contains and how to read it.
- [Commands](commands.md): running PlanExe2 by hand, options, stopping and resuming.
- [How it works](how_it_works.md): the DAG, skills, and how edits are picked up.

## PlanExe v1

The v1 documentation (MCP server, web frontends, Docker, OpenRouter/Ollama/LM Studio providers) is in the
[PlanExe repository](https://github.com/PlanExeOrg/PlanExe/tree/main/docs). PlanExe2 does not have these
components.

Source: [github.com/PlanExeOrg/PlanExe2](https://github.com/PlanExeOrg/PlanExe2).
