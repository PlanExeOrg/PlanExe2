---
name: identify_purpose
description: Classify the plan as business, personal or other, and flag non-profit plans, so downstream prompts can be tailored.
inputs: [plan.txt]
outputs: [identify_purpose_raw.json, identify_purpose.md]
tier: high
fact_check: false
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, user prompt = plan.txt, schema `schema.json`
(topic, purpose_detailed, purpose, non_profit). "other" doubles as the low-confidence bucket.

Tweak vs PlanExe: a non_profit flag. A business plan that is not run for profit (public sector, NGO, an industry
consortium establishing a shared standard, open source) selects the `business_non_profit` prompt variants
(planexe_skill/shared/purpose.py), which judge it by the value it delivers and funding accountability instead of
ROI or revenue.
