---
name: related_resources
description: Suggest real past or existing projects similar to this one, as references (lessons, risks, contacts).
inputs: [canonical_facts.json, plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan_raw.json]
outputs: [related_resources_raw.json, related_resources.md]
tier: mid
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, schema `schema.json` (suggestion_list of
SuggestionItem{item_index, project_name, project_description, success_metrics,
risks_and_challenges_faced, where_to_find_more_information, actionable_steps,
rationale_for_suggestion}, summary). User prompt = "File '<name>':" sections for initial-plan.txt,
strategic_decisions.md, scenarios.md, assumptions.md (short consolidated assumptions) and
project-plan.json (compacted project_plan_raw.json). Markdown: "## Suggestion N - <name>" with
### subsections per list (items joined by newlines), then "## Summary".

Tweaks vs PlanExe: tier mid (Sonnet, low effort) and one anti-fabrication sentence in the system
prompt. With Haiku without thinking the stage lost 3/4: invented campuses, contacts, emails and
statistics (judge: "actively harmful" for a references stage).
