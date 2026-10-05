---
name: governance_phase6_extra
description: Validate the prior governance phases (consistency, gaps), pose tough questions, and summarize the governance approach.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan_raw.json, governance_phase1_audit_raw.json, governance_phase2_bodies_raw.json, governance_phase3_impl_plan_raw.json, governance_phase4_decision_escalation_matrix_raw.json, governance_phase5_monitoring_progress_raw.json]
outputs: [governance_phase6_extra_raw.json, governance_phase6_extra.md]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/governance.py]
max_items_per_list: 6
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(governance_validation_checks, tough_questions, summary). User prompt = "File '<name>':" sections
for initial-plan.txt, strategic_decisions.md, scenarios.md, assumptions.md, project-plan.json and
the raw JSON of governance phases 1-5. Markdown: "## Governance Validation Checks" and
"## Tough Questions" as numbered lists, then "## Summary".
