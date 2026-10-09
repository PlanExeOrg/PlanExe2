---
name: filter_documents_to_find
description: Narrow the documents-to-find list to the most relevant ones for the current plan.
inputs: [canonical_facts.json, identify_purpose_raw.json, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, identified_documents_to_find.json]
outputs: [filter_documents_to_find_raw.json, filter_documents_to_find_clean.json]
tier: low
est_llm_calls: 1
uses: [planexe_skill/shared/documents.py, planexe_skill/shared/purpose.py]
judge: [filter_documents_to_find_raw.json]
---
Shared logic in `planexe_skill/shared/documents.py` (run_filter). The documents in
identified_documents_to_find.json are reduced to `{id: <int>, name: "<document_name>\n<description>"}`
(integer ids instead of uuids) and embedded (python repr, as in PlanExe) as `File 'documents.json'`
after the strategic_decisions.md, scenarios.md, assumptions.md (= consolidate_assumptions_short.md)
and project-plan.md sections. The purpose in identify_purpose_raw.json selects the system prompt
(`prompts/business_for_profit.md` / `business_non_profit.md` / `business_other.md` /
`personal.md` / `other.md`). One structured call, schema `schema.json`
(document_list[] {id, rationale, impact_rating Critical/High/Medium/Low}, summary).

Selection (code): keep all Critical; while fewer than 5 kept, add all High, then Medium, then Low.
The clean output is the original document list filtered to the kept ids (original order).
Raw = response + metadata + system_prompt + user_prompt.
