---
name: create_wbs_level1
description: Extract the project title and final deliverable (WBS Level 1) from the project plan.
inputs: [canonical_facts.json, project_plan_raw.json]
outputs: [wbs_level1_raw.json, wbs_level1.json, wbs_level1_project_title.json]
tier: low
est_llm_calls: 1
judge: [wbs_level1.json]
---
One structured call with no system prompt (as in PlanExe): user prompt = `prompts/query_preamble.md`
+ project_plan_raw.json compacted (metadata/user_prompt/system_prompt dropped), schema `schema.json`
(WBSLevel1: project_title, final_deliverable; both 1-3 words).

Outputs: the raw response with `metadata` (incl. `query`), the clean dict
`{id: uuid4, project_title, final_deliverable}`, and the bare project title as text in
`wbs_level1_project_title.json` (PlanExe writes plain text there despite the extension).
