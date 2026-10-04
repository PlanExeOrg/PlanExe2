---
name: candidate_scenarios
description: Generate aggressive, moderate, and conservative scenarios from the vital few levers.
inputs: [vital_few_levers_raw.json, identify_purpose.md, plan_type.md, plan.txt]
outputs: [candidate_scenarios_raw.json, candidate_scenarios.json]
tier: high
est_llm_calls: 1
---
One structured call (system prompt `prompts/system.md`, schema `schema.json`). User prompt =
`**Project Context:**` (plan.txt, purpose.md, plan_type.md) + `**Vital Levers & Options:**` (per
vital lever: name, its review as "Description", options list). The model returns analysis_title,
core_tension and exactly 3 scenarios (Pioneer / Builder / Consolidator archetypes), each with
strategic_logic and lever_settings (lever name -> one of that lever's options).
candidate_scenarios.json = the response; raw adds metadata and prompts.
