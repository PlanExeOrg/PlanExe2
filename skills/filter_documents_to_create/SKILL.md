---
name: filter_documents_to_create
description: Narrow the documents-to-create list to the most relevant ones for the current plan.
inputs: [identify_purpose_raw.json, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, identified_documents_to_create.json]
outputs: [filter_documents_to_create_raw.json, filter_documents_to_create_clean.json]
tier: mid
est_llm_calls: 1
uses: [planexe_skill/shared/documents.py]
judge: [filter_documents_to_create_raw.json]
---
Shared logic in `planexe_skill/shared/documents.py` (run_filter). The documents in
identified_documents_to_create.json are reduced to `{id: <int>, name: "<document_name>\n<description>"}`
(integer ids instead of uuids) and embedded (python repr, as in PlanExe) as `File 'documents.json'`
after the strategic_decisions.md, scenarios.md, assumptions.md (= consolidate_assumptions_short.md)
and project-plan.md sections. The purpose in identify_purpose_raw.json selects the system prompt
(`prompts/business.md` / `personal.md` / `other.md`). One structured call, schema `schema.json`
(document_list[] {id, rationale, impact_rating Critical/High/Medium/Low}, summary).

Selection (code): keep all Critical; while fewer than 5 kept, add all High, then Medium, then Low.
The clean output is the original document list filtered to the kept ids (original order).
Raw = response + metadata + system_prompt + user_prompt.

Tier high (prompts verbatim): with Haiku the ratings were poorly calibrated (most documents
'Critical', so the filter barely narrowed), rationales were long and the summary's counts did not
match the ratings (3/4 judge losses; a calibration prompt tweak only got to 2/4). Sonnet with the
verbatim prompts wins 4/4.
