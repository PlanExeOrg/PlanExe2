---
name: executive_summary
description: Produce a concise one-pager for decision-makers with key findings and recommendations.
inputs: [canonical_facts.json, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, data_collection.md, related_resources.md, swot_analysis.md, team.md, pitch.md, expert_criticism.md, wbs_project_level1_and_level2_and_level3.csv, review_plan.md]
outputs: [executive_summary_raw.json, executive_summary.md]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/final_review.py]
max_words_per_field: 60
max_items_per_list: 5
---
One structured call: system prompt `prompts/system.md`, schema `schema.json` (audience_tailoring,
focus_and_context, purpose_and_goals, key_deliverables_and_outcomes, timeline_and_budget,
risks_and_mitigations, action_orientation, overall_takeaway, feedback). User prompt = the 11 review
documents (see review_plan) + `File 'review-plan.md'`.

Markdown: one `## ` section per field (Focus and Context, Purpose and Goals, Key Deliverables and
Outcomes, Timeline and Budget, Risks and Mitigations, Audience Tailoring, Action Orientation, Overall
Takeaway, Feedback), then fix_bullet_lists. Raw = response + markdown + metadata + prompts.
