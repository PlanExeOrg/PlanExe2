---
name: governance_phase5_monitoring_progress
description: How progress, critical success factors and major risks are monitored, and what triggers plan adaptation.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan_raw.json, governance_phase2_bodies_raw.json, governance_phase3_impl_plan_raw.json, governance_phase4_decision_escalation_matrix_raw.json]
outputs: [governance_phase5_monitoring_progress_raw.json, governance_phase5_monitoring_progress.md]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/governance.py]
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(monitoring_progress: approach, monitoring_tools_platforms, frequency, responsible_role,
adaptation_process, adaptation_trigger). User prompt = "File '<name>':" sections for
initial-plan.txt, strategic_decisions.md, scenarios.md, assumptions.md, project-plan.json,
governance-phase2-bodies.json, governance-phase3-impl-plan.json and
governance-phase4-decision-escalation-matrix.json. Markdown: "### N. <approach>" per item.
