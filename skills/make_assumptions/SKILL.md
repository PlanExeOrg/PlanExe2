---
name: make_assumptions
description: Fill information gaps with grounded assumptions about costs, timelines, and resources.
inputs: [plan.txt, identify_purpose.md, plan_type.md, strategic_decisions.md, scenarios.md, physical_locations.md, currency_strategy.md, identify_risks.md]
outputs: [make_assumptions_raw.json, make_assumptions.json, make_assumptions.md]
tier: low
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, schema `schema.json`
(question_assumption_list[{item_index, question, assumptions, assessments}]). The prompt asks for
exactly eight items, one per critical planning area (funding, timeline, resources, governance,
safety, environment, stakeholders, operational systems).
User prompt concatenates plan.txt, purpose.md, plan_type.md, strategic_decisions.md, scenarios.md,
physical_locations.md, currency_strategy.md and identify_risks.md as `File '<name>':` sections.

Outputs: the raw response, `make_assumptions.json` (list of {question, assumptions, assessments},
read by distill_assumptions) and markdown with one `## Question N - <question>` section per item.
