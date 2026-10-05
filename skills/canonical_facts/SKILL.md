---
name: canonical_facts
description: Reconcile the plan's key numbers and dates into one canonical fact table that every later stage must use.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, pre_project_assessment.json]
outputs: [canonical_facts.json, canonical_facts.md]
tier: high
fact_check: false
est_llm_calls: 2
---
Not part of the original PlanExe pipeline. Added after the Codex review of the datacenter run: stages
invented their own values for the same quantity (RTE gate 250/300/500 MW, tenant price vs power cost,
permit timing, remediation thresholds), and a final consistency check could only report that.

Runs right before project_plan, so the project plan (which most later stages build on) is written from
the facts. One reasoning call reads the user's prompt, strategic decisions, scenarios, assumptions and the
pre-project assessment, resolves conflicts and
returns 15-40 canonical facts (snake_case key, value with unit, kind, basis). Every later LLM stage
declares `canonical_facts.json` as an input; the runtime then adds the table to its system prompt with
the rule to use these values and not introduce different ones (`planexe_skill/context.py`).

History: first placed after project_plan; a full datacenter run then showed later stages siding with the
unreconciled project plan (e.g. FID at Month 12 vs canonical Month 24), so it moved before it.

A second reasoning call (`prompts/verify.md`) recomputes the table's arithmetic and removes internal
conflicts (e.g. a reserve counted inside and outside the contingency) before any later stage uses it.
