---
name: review_team
description: Review and validate the assembled team composition.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, pre_project_assessment.json, project_plan.md, related_resources.md, enrich_team_members_environment_info.json]
outputs: [review_team_raw.json]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/team.py, planexe_skill/shared/team_markdown_document.py]
---
The enriched team (enrich_team_members_environment_info.json) is rendered to markdown with the vendored
TeamMarkdownDocumentBuilder (`append_roles(..., title=None)`) and inserted as `File 'team-members.md'` into
the shared team context (`initial-plan.txt`, `strategic_decisions.md`, `scenarios.md`, `assumptions.md` =
consolidate_assumptions_short.md, `pre-project-assessment.json`, `project-plan.md`, `related-resources.md`).
One structured call: system prompt `prompts/system.md`, schema `schema.json` (omissions and
potential_improvements, each a list of {issue, explanation, recommendation}).
