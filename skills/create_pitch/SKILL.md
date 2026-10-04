---
name: create_pitch
description: Create a compelling project pitch with target audience, call to action, and risk mitigation.
inputs: [strategic_decisions.md, scenarios.md, project_plan.md, wbs_project_level1_and_level2.json, related_resources.md]
outputs: [pitch_raw.json]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/schedule]
---
One structured call with no system prompt (as in PlanExe: `sllm.complete(QUERY_PREAMBLE + query)`):
user prompt = `prompts/query_preamble.md` + `File '<name>':` sections for strategic_decisions.md,
scenarios.md, project_plan.md, `Work Breakdown Structure.json` (wbs_project_level1_and_level2.json
round-tripped through WBSProject and compacted) and `similar_projects.md` (= related_resources.md).
Schema `schema.json` (ProjectPitch: pitch, why_this_pitch_works, target_audience, call_to_action,
risks_and_mitigation, metrics_for_success, stakeholder_benefits, ethical_considerations,
collaboration_opportunities, long_term_vision). Output = response + metadata + query.
