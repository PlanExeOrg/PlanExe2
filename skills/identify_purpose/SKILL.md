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

Tweak vs PlanExe: a profit_motive (for_profit, non_profit, other), kept in identify_purpose_raw.json only.
identify_purpose.md says `**Purpose:** business` for every business plan, so downstream stages see what PlanExe
showed them. The skills that use planexe_skill/shared/purpose.py append a short addendum to their business prompt
for non_profit (NGO, an industry consortium establishing a shared standard, open source) and other (a government
programme, an agreement between countries, a public-private hybrid) business plans.
