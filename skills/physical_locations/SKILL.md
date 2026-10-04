---
name: physical_locations
description: Determine where the project operates — extract or suggest physical locations.
inputs: [plan.txt, identify_purpose.md, plan_type_raw.json, plan_type.md, strategic_decisions.md, scenarios.md]
outputs: [physical_locations_raw.json, physical_locations.md]
tier: low
est_llm_calls: 1
---
If `plan_type_raw.json` says the plan is not "physical", no LLM call is made: the raw file is
`{"comment": ...}` and the markdown says the plan is purely digital.

Otherwise one structured call: system prompt `prompts/system.md`, schema `schema.json`
(has_location_in_plan, requirements_for_the_physical_locations, physical_locations[], location_summary).
User prompt concatenates plan.txt, purpose.md, plan_type.md, strategic_decisions.md and scenarios.md
as `File '<name>':` sections. The prompt asks for three location suggestions (plus the user's own
location when one is given).
