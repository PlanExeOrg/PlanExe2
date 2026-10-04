---
name: select_scenario
description: Evaluate trade-offs and select the best scenario with a rationale.
inputs: [candidate_scenarios.json, vital_few_levers_raw.json, identify_purpose.md, plan_type.md, plan.txt]
outputs: [selected_scenario_raw.json, selected_scenario.json]
tier: high
est_llm_calls: 1
---
One structured call (system prompt `prompts/system.md`, schema `schema.json`). User prompt =
`**Project Plan:**` (fenced: plan.txt, purpose.md, plan_type.md, compact JSON of the vital levers and
of the candidate scenarios) + `**Strategic Scenarios for Evaluation:**` (scenarios as indented JSON).
Three-step analysis: plan characteristics (ambition, risk, complexity, domain, holistic profile),
a 1-10 fit score per scenario, and the final choice with a bullet-point justification.
selected_scenario.json = the response; raw adds metadata and prompts.
