---
name: review_assumptions
description: Flag unreasonable, missing, or contradictory assumptions with recommendations.
inputs: [identify_purpose.md, plan_type.md, strategic_decisions.md, scenarios.md, physical_locations.md, currency_strategy.md, identify_risks.md, make_assumptions.md, distill_assumptions.md]
outputs: [review_assumptions_raw.json, review_assumptions.md]
tier: low
est_llm_calls: 1
max_items_per_list: 6
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(expert_domain, domain_specific_considerations[], issues[{issue, explanation, recommendation,
sensitivity}], conclusion). Note: plan.txt is NOT part of the input (as in PlanExe).
User prompt = the nine upstream markdown documents, each as `# <Title>\n\n<content>`, joined with
blank lines (a missing file becomes a "**Problem with document:**" chunk). The prompt focuses on
critical missing assumptions, the three most important issues and quantified sensitivity ranges.
