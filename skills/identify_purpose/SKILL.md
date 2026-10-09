---
name: identify_purpose
description: Classify the plan as business, personal or other, and its profit motive, so downstream prompts can be tailored.
inputs: [plan.txt]
outputs: [identify_purpose_raw.json, identify_purpose.md]
tier: high
fact_check: false
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, user prompt = plan.txt, schema `schema.json`
(topic, purpose_detailed, purpose, profit_motive). "other" doubles as the low-confidence bucket.

Tweak vs PlanExe: a profit_motive (for_profit, non_profit, other). Downstream, a business plan selects the
`business_for_profit`, `business_non_profit` (NGO, an industry consortium establishing a shared standard, open
source) or `business_other` (a government programme, an agreement between countries, a public-private hybrid)
prompt variant (planexe_skill/shared/purpose.py). The last two judge the plan by its outcomes and funding
accountability instead of ROI or revenue.
