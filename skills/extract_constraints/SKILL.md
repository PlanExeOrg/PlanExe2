---
name: extract_constraints
description: Extract the explicit positive (wanted) and negative (to avoid) constraints stated in the user's prompt.
inputs: [plan.txt]
outputs: [extract_constraints_raw.json, extract_constraints.md]
tier: high
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, user prompt = plan.txt, schema `schema.json`.
Later constraint-checker stages verify that the levers/scenarios respect these constraints.
