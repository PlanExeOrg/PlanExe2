---
name: governance_phase3_impl_plan
description: Step-by-step plan for setting up the governance bodies (who drafts ToR, appoints members, holds kick-offs).
inputs: [canonical_facts.json, plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan_raw.json, governance_phase2_bodies_raw.json]
outputs: [governance_phase3_impl_plan_raw.json, governance_phase3_impl_plan.md]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/governance.py]
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(governance_implementation_plan: step_description, responsible_body_or_role, suggested_timeframe,
key_outputs_deliverables, dependencies). User prompt = "File '<name>':" sections for
initial-plan.txt, strategic_decisions.md, scenarios.md, assumptions.md, project-plan.json and
governance-phase2-bodies.json (both compacted raw JSON). Markdown: "### N. <step>" per step.
