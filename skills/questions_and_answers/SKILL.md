---
name: questions_and_answers
description: Anticipate stakeholder questions and provide clear answers from the plan.
inputs: [strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, data_collection.md, related_resources.md, swot_analysis.md, team.md, pitch.md, expert_criticism.md, wbs_project_level1_and_level2_and_level3.csv, review_plan.md]
outputs: [questions_and_answers_raw.json, questions_and_answers.md]
tier: low
est_llm_calls: 2
parallel_llm: 1
uses: [planexe_skill/shared/final_review.py]
max_words_per_field: 80
---
User prompt = the 11 review documents (see review_plan) + `File 'review-plan.md'`. (The PlanExe node
also *requires* consolidate_governance and documents_to_create_and_find but never reads them.)

Two structured calls with `prompts/system.md`, schema `schema.json` (question_answer_pairs[item_index,
question, answer, rationale] x5, summary). Call 2 continues the chat with `prompts/second_user.md`
("Generate 5 additional ..."); the first response is embedded in the user message as the prior
conversation, so the calls are sequential. Pairs are merged (call-2 item_index offset by the call-1
count), summaries joined with a blank line.

Markdown: `**Q<n>: question**` / `A<n>: answer` paragraphs.
