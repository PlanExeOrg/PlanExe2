---
name: create_wbs_level3
description: Break Level 2 tasks into detailed subtasks (WBS Level 3).
inputs: [project_plan_raw.json, wbs_project_level1_and_level2.json, task_durations.json, data_collection.md]
outputs: [wbs_level3.json, wbs_level3_{n}_raw.json]
tier: low
est_llm_calls: 40
parallel_llm: 6
uses: [planexe_skill/shared/schedule]
---
The level 1+2 WBS is extended with the duration estimates (vendored WBSPopulate). Every leaf task
is decomposed by one independent structured call (run concurrently), no system prompt (as in
PlanExe: `sllm.complete(QUERY_PREAMBLE + query)`): user prompt = `prompts/query_preamble.md`
("Split the task into 3 to 5 subtasks...") + "The project plan:" (project_plan_raw.json compacted)
+ "Data collection:" + "Work breakdown structure:" (WBS with durations, compacted) + "Only
decompose this task:" (quoted uuid). Schema `schema.json` (WBSTaskDetails: subtasks[] with name,
description, resources_needed[]).

Cleanup (code): each subtask gets a uuid4 `id` and `parent_id` = the decomposed task.
Outputs: wbs_level3_{n}_raw.json per leaf (response + metadata + query, n from 1) and
wbs_level3.json = all subtasks concatenated in leaf order. A failed call fails the stage (as in PlanExe).
