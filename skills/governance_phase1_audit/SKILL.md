---
name: governance_phase1_audit
description: Governance audit framework - corruption risks, misallocation risks, audit procedures, transparency measures.
inputs: [canonical_facts.json, plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md]
outputs: [governance_phase1_audit_raw.json, governance_phase1_audit.md]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/governance.py]
max_items_per_list: 6
---
One structured call: system prompt `prompts/system.md`, schema `schema.json` (corruption_list,
misallocation_list, audit_procedures, transparency_measures). User prompt = "File '<name>':" sections
for initial-plan.txt, strategic_decisions.md, scenarios.md, assumptions.md (the short consolidated
assumptions) and project-plan.md. Markdown: one "## Audit - ..." section per list.
