---
name: expert_review
description: Assemble a panel of domain experts and have them critique the plan.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, pre_project_assessment.json, project_plan.md, swot_analysis.md]
outputs: [experts_raw.json, experts.json, expert_criticism_{n}_raw.json, expert_criticism.md]
tier: low
est_llm_calls: 4
parallel_llm: 2
---
Query = `File 'initial-plan.txt'`, `strategic_decisions.md`, `scenarios.md`, `pre-project assessment.json`,
`project_plan.md`, `SWOT Analysis.md` sections.

Phase 1 (ExpertFinder): system prompt `prompts/expert_finder.md`, schema `schema_experts.json`; call 1 =
query, call 2 = follow-up "4 more please" (PlanExe sends it as a chat turn after the first assistant
response; here the first response is embedded in the user message as the prior conversation). Experts of
both calls are merged, given uuid4 ids and renamed (title, knowledge, why, what, skills, search_query) ->
experts.json; experts_raw.json = merged response + metadata {result1, result2} + prompts.

Phase 2 (ExpertCriticism): the first 2 experts (max_expert_count) each critique the query with
`prompts/expert_criticism.md` (PLACEHOLDER_ROLE/KNOWLEDGE/SKILLS filled from the expert), schema
`schema_criticism.json`; independent calls run concurrently. expert_criticism_{n}_raw.json = response +
metadata + query. A failing critic fails the stage (as in PlanExe).

expert_criticism.md: per expert an info block + Primary/Secondary Actions, Follow Up Consultation, and
per issue A-E subsections; then the experts without feedback are listed.
