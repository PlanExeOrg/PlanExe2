---
name: enrich_team_members_with_environment_info
description: Add equipment needs and facility requirements for each team member's role.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, pre_project_assessment.json, project_plan.md, related_resources.md, enrich_team_members_background_story.json]
outputs: [enrich_team_members_environment_info_raw.json, enrich_team_members_environment_info.json]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/team.py]
---
One structured call (system prompt `prompts/system.md`, schema `schema.json`). User prompt = the shared team
context (`initial-plan.txt`, `strategic_decisions.md`, `scenarios.md`, `assumptions.md` =
consolidate_assumptions_short.md, `pre-project-assessment.json`, `project-plan.md`) +
`team-members-that-needs-to-be-enriched.json` (enrich_team_members_background_story.json, compact JSON) + `related-resources.md`.

The response (team_members: id, equipment_needs, facility_needs) is merged into the input list by id as
equipment_needs, facility_needs.
