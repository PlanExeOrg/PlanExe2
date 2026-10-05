---
name: create_wbs_level2
description: Decompose top-level phases into major tasks (WBS Level 2).
inputs: [canonical_facts.json, strategic_decisions.md, scenarios.md, project_plan.md, wbs_level1.json, data_collection.md]
outputs: [wbs_level2_raw.json, wbs_level2.json]
tier: low
est_llm_calls: 1
judge: [wbs_level2.json]
---
One structured call with no system prompt (as in PlanExe: `sllm.complete(QUERY_PREAMBLE + query)`):
user prompt = `prompts/query_preamble.md` + `File '<name>':` sections for strategic_decisions.md,
scenarios.md, project_plan.md, `WBS Level 1.json` (wbs_level1.json compacted) and
data_collection.md. Schema `schema.json` (WorkBreakdownStructure: major_phase_details[] with
major_phase_wbs_number, major_phase_title, subtasks[] {subtask_wbs_number, subtask_title}).

Cleanup (code): every major phase and subtask gets a uuid4 `id`; wbs_level2.json =
`[{id, major_phase_title, subtasks: [{id, description=subtask_title}]}]`.
Raw = response + metadata + query. Tier high: this defines the plan's phase structure.

Tweak vs PlanExe: the preamble asks for planning granularity (typically 4-8 phases x 3-6 subtasks).
Without it Sonnet produced 11-17 phases / 77-123 subtasks (baselines: 3-7 / 17-35), which tripled
the level-3 and duration fan-out and pushed a full run far past the 45-minute budget.
