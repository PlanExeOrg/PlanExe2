---
name: governance_phase2_bodies
description: Define the internal governance bodies (steering, operational, advisory/assurance) with membership, decision rights and escalation paths.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, governance_phase1_audit.md]
outputs: [governance_phase2_bodies_raw.json, governance_phase2_bodies.md]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/governance.py]
max_items_per_list: 6
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(internal_governance_bodies: name, rationale_for_inclusion, responsibilities, initial_setup_actions,
membership, decision_rights, decision_mechanism, meeting_cadence, typical_agenda_items,
escalation_path). User prompt = "File '<name>':" sections for initial-plan.txt,
strategic_decisions.md, scenarios.md, assumptions.md, project-plan.md and
governance-phase1-audit.md. Markdown: "### N. <name>" per body with bold fields and bullet lists.
