---
name: enrich_team_members_with_contract_type
description: Determine contract type for each team member.
inputs: [canonical_facts.json, plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, pre_project_assessment.json, project_plan.md, related_resources.md, find_team_members.json]
outputs: [enrich_team_members_contract_type_raw.json, enrich_team_members_contract_type.json]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/team.py]
---
One structured call (system prompt `prompts/system.md`, schema `schema.json`). User prompt = the shared team
context (`initial-plan.txt`, `strategic_decisions.md`, `scenarios.md`, `assumptions.md` =
consolidate_assumptions_short.md, `pre-project-assessment.json`, `project-plan.md`) +
`team-members-that-needs-to-be-enriched.json` (find_team_members.json, compact JSON) + `related-resources.md`.

The response (team_members: id, contract_type, justification) is merged into the input list by id as
contract_type, contract_type_justification.
