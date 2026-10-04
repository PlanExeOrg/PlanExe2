---
name: identify_purpose
description: Classify the plan as business, personal or other so downstream prompts can be tailored.
inputs: [plan.txt]
outputs: [identify_purpose_raw.json, identify_purpose.md]
tier: high
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, user prompt = plan.txt, schema `schema.json`
(topic, purpose_detailed, purpose). "other" doubles as the low-confidence bucket.
