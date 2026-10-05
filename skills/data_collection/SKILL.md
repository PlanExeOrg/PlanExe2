---
name: data_collection
description: Specify data-gathering actions needed to validate the plan: market, financial, regulatory, etc.
inputs: [strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, related_resources.md, swot_analysis.md, team.md, expert_criticism.md]
outputs: [data_collection_raw.json, data_collection.md]
tier: low
est_llm_calls: 1
max_words_per_field: 80
max_items_per_list: 5
---
One structured call: system prompt `prompts/system.md`, schema `schema.json` (data_collection_list of
{item_index, title, data_to_collect, simulation_steps, expert_validation_steps, rationale,
responsible_parties, assumptions [{item_index, assumption, sensitivity_score low|medium|high}],
smart_validation_objective, notes} + summary). User prompt = `File 'strategic_decisions.md'`,
`scenarios.md`, `assumptions.md` (= consolidate_assumptions_short.md), `project-plan.md`,
`related-resources.md`, `swot-analysis.md`, `team.md`, `expert-review.md` (= expert_criticism.md) sections
(PlanExe does not pass plan.txt here).

data_collection.md: per item `## N. title`, rationale, then Data to Collect / Simulation Steps / Expert
Validation Steps / Responsible Parties / Assumptions (`**Sensitivity:** text`) / SMART Validation
Objective / Notes; final `## Summary`.

Tweak vs PlanExe: a scope/length budget (5-7 most critical areas, concise fields). Without it Haiku
wrote 10-12 long items (25k-58k output tokens, 5-27 minutes, one 900 s timeout); baselines have 3-4.
