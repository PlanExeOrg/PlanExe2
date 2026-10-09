---
title: How it works
---

# How it works

## A DAG of skills

Plan generation is a pipeline of about 75 stages. Each stage is a **skill**: a folder in `skills/` with its
prompts, an output schema and a small `run.py`. A dependency-free Python runner (`planexe_skill/`) executes
them as a DAG, with up to 4 LLM calls in parallel by default.

Edges are derived from file names: a stage depends on whichever stage produces one of its inputs. Run
`python3 -m planexe_skill graph` to list the stages in order, or `graph --dot` for Graphviz.

## A skill folder

```
skills/identify_purpose/
  SKILL.md        frontmatter (inputs, outputs, tier, est_llm_calls) + description
  prompts/        system prompts, verbatim from PlanExe v1 unless noted
  schema.json     JSON schema for structured output
  run.py          def run(ctx): reads inputs, calls ctx.llm(...), writes outputs
```

A skill may only read the files listed in its `inputs` and write the files listed in its `outputs`; the
runner enforces this.

## Tiers

Each skill's `tier` picks the model:

| tier | default model | used for |
|---|---|---|
| `high` | Sonnet, high effort | the foundational early stages |
| `mid` | Sonnet, low effort | later stages where the fast model isn't good enough |
| `low` | Haiku, no extended thinking | everything else |

Override with `--model-high`, `--model-mid` and `--model-low` (see [Commands](commands.md#options-for-run)).

## Intermediary files

Every stage writes plain JSON and markdown files, all in the run directory. The report is assembled from
them at the end.

## Dirtiness

`RUN_DIR/.planexe_skill/manifest.json` stores, for every stage, hashes of its skill folder, its input files
and its output files. A stage is **dirty**, and re-runs, when:

- one of its outputs is missing,
- its skill folder changed, or
- one of its inputs changed.

`python3 -m planexe_skill status RUN_DIR` shows which stages are dirty and why.

## Editing and re-running

You can edit any intermediary file by hand, for example to correct a budget in an early stage or rewrite
an assumption. On the next `run`:

- your edited file is kept (the stage that produced it is not re-run over your edit),
- every stage downstream of it is dirty and is regenerated from your version.

Hand-edited files are listed in the report's Metadata section.

To regenerate a stage instead of editing it, use `run RUN_DIR --force STAGE`, or `--force-downstream STAGE`
to also regenerate everything after it.

## Stages added by PlanExe2

These stages are not in PlanExe v1:

| stage | what it does |
|---|---|
| `canonical_facts` | one table of key numbers and dates, produced before the project plan |
| `consistency_review` | lints the core documents against the canonical facts |
| `consistency_repair` | repairs them with exact edits, including deterministic arithmetic fixes |
| `decision_register` | the open decisions as options, consequences, owner and deadline, plus the choices to ratify |
| `arithmetic_check` | deterministic re-computation of every written calculation |
