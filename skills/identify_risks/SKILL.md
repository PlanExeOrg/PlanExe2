---
name: identify_risks
description: Build a risk register covering strategic, operational, financial, and location-specific risks.
inputs: [plan.txt, identify_purpose.md, plan_type.md, strategic_decisions.md, scenarios.md, physical_locations.md, currency_strategy.md]
outputs: [identify_risks_raw.json, identify_risks.md]
tier: high
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(risks[{risk_area, risk_description, potential_impact, likelihood, severity, action}],
risk_assessment_summary). likelihood/severity are low|medium|high.
User prompt concatenates plan.txt, purpose.md, plan_type.md, strategic_decisions.md, scenarios.md,
physical_locations.md and currency_strategy.md as `File '<name>':` sections.
Markdown: one `## Risk N - <area>` section per risk, then `## Risk summary`.
