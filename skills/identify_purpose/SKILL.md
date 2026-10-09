---
name: identify_purpose
description: Classify the plan as business, public_good, personal or other so downstream prompts can be tailored.
inputs: [plan.txt]
outputs: [identify_purpose_raw.json, identify_purpose.md]
tier: high
fact_check: false
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, user prompt = plan.txt, schema `schema.json`
(topic, purpose_detailed, purpose). "other" doubles as the low-confidence bucket.

Tweak vs PlanExe: a fourth purpose, "public_good" (non-profit, public-sector, public-interest), which PlanExe
files under "business". Downstream it selects public-good prompt variants that judge the plan by public value
and funding accountability instead of ROI, revenue or a "killer app".
