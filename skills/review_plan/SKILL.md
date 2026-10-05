---
name: review_plan
description: Critically review the near-final plan with targeted questions and SMART recommendations.
inputs: [canonical_facts.json, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, data_collection.md, related_resources.md, swot_analysis.md, team.md, pitch.md, expert_criticism.md, wbs_project_level1_and_level2_and_level3.csv]
outputs: [review_plan_raw.json, review_plan.md]
tier: low
est_llm_calls: 16
parallel_llm: 1
uses: [planexe_skill/shared/final_review.py]
---
Document = the 11 input files as `File '<name>':` sections (strategic_decisions.md, scenarios.md,
assumptions.md = consolidate_assumptions_short.md, project-plan.md, data-collection.md,
related-resources.md, swot-analysis.md, team.md, pitch.md, expert-review.md = expert_criticism.md,
work-breakdown-structure.csv). System prompt = `prompts/system.md` + "Document for review:" + document.

16 review questions (`questions.json`: Critical Issues ... Automation Opportunities), asked one at a
time in one growing chat, schema `schema.json` (bullet_points, exactly 3). PlanExe sends the previous
questions and answers as chat turns; here they are embedded in the user message ("## Conversation
so far"), so the calls are sequential. A failed question gets an empty answer and the conversation
continues (as in PlanExe).

Markdown: `## Review N: <title>` with numbered answers. Raw: question_answers_list + duration/byte
statistics + metadata_list + system_prompt.

Tweaks vs PlanExe: (1) one added paragraph in the system prompt — bullets at most ~80 words, later
answers as short as the first, quantifications consistent with the document's figures, no invented
organizations/events; plus `prompts/question_reminder.md` appended to the current question (not to
the history): exactly three bullets, ~80 words each, no repeats, no invented developments. Haiku
otherwise let the bullets snowball to 300-700 words as the conversation grew (the instructions sit
far above the ~100K-token document), sometimes merged the 3 bullets into one, and fabricated
"since Version 1" facts. (2) A failed question is retried once before falling back to the empty
answer (PlanExe's LLMExecutor retries too), and an answer without exactly 3 bullets is asked once more.
