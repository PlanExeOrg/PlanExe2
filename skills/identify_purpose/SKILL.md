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

Tweak vs PlanExe: a profit_motive (for_profit, non_profit, other). A business plan that is non_profit (NGO, an
industry consortium establishing a shared standard, open source) or other (a government programme, an agreement
between countries, a public-private hybrid) selects the `business_non_profit` prompt variants
(planexe_skill/shared/purpose.py), which judge it by the value it delivers and funding accountability instead of
ROI or revenue. identify_purpose.md words the two differently.
