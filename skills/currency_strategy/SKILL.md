---
name: currency_strategy
description: Choose the project currency based on physical locations and cross-border needs.
inputs: [plan.txt, identify_purpose.md, plan_type.md, strategic_decisions.md, scenarios.md, physical_locations.md]
outputs: [currency_strategy_raw.json, currency_strategy.md]
tier: low
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(money_involved, currency_list[{currency, consideration}], primary_currency, currency_strategy).
User prompt concatenates plan.txt, purpose.md, plan_type.md, strategic_decisions.md, scenarios.md and
physical_locations.md as `File '<name>':` sections. Multi-country European projects default to EUR,
unstable local currencies fall back to USD as primary.
