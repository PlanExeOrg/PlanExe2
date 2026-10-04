---
name: pre_project_assessment
description: Evaluate project viability and readiness before detailed planning.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md]
outputs: [pre_project_assessment_raw.json, pre_project_assessment.json]
tier: high
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md` (CURRENT_YEAR_PLACEHOLDER -> current year),
schema `schema.json` (expert1/expert2 {expert_title, expert_full_name, feedback_item_list[{feedback_index,
feedback_title, feedback_description}]}, combined_summary, go_no_go_recommendation). Two experts
(execution & logistics; safety, compliance & risk) each give 4 concrete "To initiate this project,
you must:" checklists, then a combined summary and an Execute Immediately / Proceed with Caution /
Do Not Execute recommendation.
User prompt concatenates plan.txt, strategic_decisions.md, scenarios.md and `assumptions.md`
(= consolidate_assumptions_short.md, as in PlanExe).

`pre_project_assessment.json` drops the expert names/titles (they confuse downstream stages into
treating them as stakeholders): {go_no_go_recommendation, combined_summary, feedback[{title, description}]}.
