---
name: identify_task_dependencies
description: Identify prerequisite relationships between WBS tasks for scheduling.
inputs: [strategic_decisions.md, scenarios.md, project_plan.md, wbs_level2.json, data_collection.md]
outputs: [task_dependencies_raw.json]
tier: low
est_llm_calls: 1
---
One structured call with no system prompt (as in PlanExe: `sllm.complete(QUERY_PREAMBLE + query)`):
user prompt = `prompts/query_preamble.md` ("Find the 10 most critical important task
dependencies...") + `File '<name>':` sections for strategic_decisions.md, scenarios.md,
project_plan.md, `Work Breakdown Structure.json` (wbs_level2.json compacted, with uuids) and
data_collection.md. Schema `schema.json` (DependencyMapping: task_dependency_details[] with
dependent_task_id, depends_on_task_id_list[], depends_on_task_explanation_list[]).
Output = response + metadata + query (consumed by create_schedule).
