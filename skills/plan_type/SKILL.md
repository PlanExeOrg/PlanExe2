---
name: plan_type
description: Decide whether the plan is purely digital or needs physical locations.
inputs: [plan.txt, classify_domain.md, identify_purpose.md]
outputs: [plan_type_raw.json, plan_type.md]
tier: high
fact_check: false
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, schema `schema.json` (explanation, plan_type).
User prompt concatenates plan.txt, classify_domain.md and identify_purpose.md (labelled 'purpose.md').
Most real-world plans are "physical"; "digital" only when no physical location is ever needed.
