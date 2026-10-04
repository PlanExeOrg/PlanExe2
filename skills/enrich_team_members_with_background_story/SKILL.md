---
name: enrich_team_members_with_background_story
description: Develop background story for each team member.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, pre_project_assessment.json, project_plan.md, related_resources.md, enrich_team_members_contract_type.json]
outputs: [enrich_team_members_background_story_raw.json, enrich_team_members_background_story.json]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/team.py]
---
One structured call (system prompt `prompts/system.md`, schema `schema.json`). User prompt = the shared team
context (`initial-plan.txt`, `strategic_decisions.md`, `scenarios.md`, `assumptions.md` =
consolidate_assumptions_short.md, `pre-project-assessment.json`, `project-plan.md`) +
`team-members-that-needs-to-be-enriched.json` (enrich_team_members_contract_type.json, compact JSON) + `related-resources.md`.

The response (team_members: id, job_background_story_of_employee, typical_job_activities) is merged into
the input list by id as typical_job_activities, background_story. (PlanExe's FAST_BUT_SKIP_DETAILS
pass-through mode is not ported; skills always run in full-detail mode.)
