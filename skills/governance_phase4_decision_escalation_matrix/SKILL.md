---
name: governance_phase4_decision_escalation_matrix
description: Decision escalation matrix - which problems/decisions escalate to which governance body, how, and why.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan_raw.json, governance_phase2_bodies_raw.json, governance_phase3_impl_plan_raw.json]
outputs: [governance_phase4_decision_escalation_matrix_raw.json, governance_phase4_decision_escalation_matrix.md]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/governance.py]
max_items_per_list: 6
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(decision_escalation_matrix: issue_type, escalation_level, approval_process, rationale,
negative_consequences). User prompt = "File '<name>':" sections for initial-plan.txt,
strategic_decisions.md, scenarios.md, assumptions.md, project-plan.json,
governance-phase2-bodies.json and governance-phase3-impl-plan.json. Markdown: one bold issue line
followed by plain "Field: value" lines per item.
