---
name: swot_analysis
description: Identify strengths, weaknesses, opportunities, and threats tailored to the plan's purpose.
inputs: [canonical_facts.json, plan.txt, strategic_decisions.md, scenarios.md, identify_purpose_raw.json, consolidate_assumptions_short.md, pre_project_assessment.json, project_plan.md, related_resources.md]
outputs: [swot_analysis_raw.json, swot_analysis.md]
tier: mid
est_llm_calls: 1
---
The purpose from identify_purpose_raw.json selects the system prompt: `prompts/business.md`,
`prompts/public_good.md`, `prompts/personal.md` or `prompts/other.md` (the latter with INSERT_USER_TOPIC_HERE /
INSERT_USER_SWOTTYPEDETAILED_HERE replaced by topic / purpose_detailed). One structured call, schema
`schema.json` (strengths, weaknesses, opportunities, threats, recommendations, strategic_objectives,
assumptions, missing_information, user_questions). User prompt = `File 'initial-plan.txt'`,
`strategic_decisions.md`, `scenarios.md`, `assumptions.md` (= consolidate_assumptions_short.md),
`pre-project-assessment.json`, `project-plan.md`, `related-resources.md` sections.

swot_analysis.md = one bulleted section per list (emoji headings as in PlanExe), no topic/purpose/metadata.
raw = {query, topic, purpose, purpose_detailed, response_purpose, response_conduct (+metadata), metadata (+query)}.

Tweak vs PlanExe: tier mid (Sonnet, low effort). With Haiku without thinking it lost 2/4
(deadlines before the plan date, physically impossible claims, misplaced facts).
