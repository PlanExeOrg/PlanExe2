---
name: estimate_task_durations
description: Estimate realistic, minimum, and maximum durations for each WBS task bottom-up.
inputs: [project_plan_raw.json, wbs_project_level1_and_level2.json]
outputs: [task_durations.json, task_durations_{n}_raw.json]
tier: low
est_llm_calls: 14
parallel_llm: 6
uses: [planexe_skill/shared/schedule]
---
The ids of all tasks below the WBS root (each level-2 phase followed by its subtasks, depth-first)
are split into chunks of 3. One independent structured call per chunk (run concurrently), no
system prompt (as in PlanExe: `sllm.complete(QUERY_PREAMBLE + query)`): user prompt =
`prompts/query_preamble.md` + "The project plan:" (project_plan_raw.json compacted) + "The Work
Breakdown Structure (WBS):" (the root's children as JSON) + "Only estimate these 3 tasks:" (quoted
uuids). Schema `schema.json` (TimeEstimates: task_details[] with task_id, delay_risks,
mitigation_strategy, days_min, days_max, days_realistic).

Outputs: task_durations_{n}_raw.json per chunk (response + metadata + query, n from 1) and
task_durations.json = all task_details concatenated in chunk order. A failed chunk fails the stage
(as in PlanExe).
