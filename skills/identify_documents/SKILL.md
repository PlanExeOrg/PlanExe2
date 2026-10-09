---
name: identify_documents
description: List documents the project needs — permits, contracts, specs, research, etc.
inputs: [canonical_facts.json, identify_purpose_raw.json, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, related_resources.md, swot_analysis.md, team.md, expert_criticism.md]
outputs: [identified_documents_raw.json, identified_documents.md, identified_documents_to_find.json, identified_documents_to_create.json]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/documents.py, planexe_skill/shared/purpose.py]
judge: [identified_documents.md]
max_words_per_field: 80
---
The purpose in identify_purpose_raw.json selects the system prompt (`prompts/business_for_profit.md`,
`prompts/business_non_profit.md`, `prompts/business_other.md`, `prompts/personal.md`, `prompts/other.md`). One structured call, schema `schema.json`
(DocumentDetails: documents_to_create, documents_to_find, documents_to_create_part2,
documents_to_find_part2). User prompt = `File '<name>':` sections for strategic_decisions.md,
scenarios.md, assumptions.md (= consolidate_assumptions_short.md), project-plan.md,
related-resources.md, swot-analysis.md, team.md, expert-review.md (= expert_criticism.md).

Cleanup (code): part1 + part2 are concatenated, each document gets a uuid4 `id`, optional fields
default to null. Outputs: the raw response (+metadata, system_prompt, user_prompt), the cleaned
documents to create / to find as JSON lists, and a markdown rendering (`## Documents to Create`,
`## Documents to Find`, one `### n. name` block per document).
