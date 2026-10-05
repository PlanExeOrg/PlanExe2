---
name: find_team_members
description: Identify team members required for project execution.
inputs: [canonical_facts.json, plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, pre_project_assessment.json, project_plan.md, related_resources.md]
outputs: [find_team_members_raw.json, find_team_members.json]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/team.py]
---
One structured call: system prompt `prompts/system.md` (exactly 8 candidate roles), schema `schema.json`
(brainstorm_of_needed_team_members: job_category_title, short_explanation, people_needed,
consequences_of_not_having_this_role). User prompt = `File 'initial-plan.txt'`, `strategic_decisions.md`,
`scenarios.md`, `assumptions.md` (= consolidate_assumptions_short.md), `pre-project-assessment.json`,
`project-plan.md`, `related-resources.md` sections.

find_team_members.json = roles renamed to {id (1-based), category, explanation, consequences, count}.
