---
name: draft_documents_to_create
description: Draft content specs for each document to create: essential info, risks, and scenarios.
inputs: [canonical_facts.json, identify_purpose_raw.json, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, filter_documents_to_create_clean.json]
outputs: [draft_documents_to_create.json, draft_documents_to_create_{n}_raw.json]
tier: low
est_llm_calls: 5
parallel_llm: 5
uses: [planexe_skill/shared/documents.py]
---
Shared logic in `planexe_skill/shared/documents.py` (run_draft). One independent structured call
per document in filter_documents_to_create_clean.json (they run concurrently). The purpose in
identify_purpose_raw.json selects the system prompt (`prompts/business.md` / `public_good.md` / `personal.md` /
`other.md`). User prompt = strategic_decisions.md, scenarios.md, assumptions.md
(= consolidate_assumptions_short.md), project-plan.md and `File 'document.json'` (python repr of
the document dict, as in PlanExe). Schema `schema.json` (essential_information[],
risks_of_poor_quality[], worst_case_scenario, best_case_scenario, fallback_alternative_approaches[]).

Outputs: draft_documents_to_create_{n}_raw.json per document (response + metadata + system_prompt + user_prompt, n from 1)
and draft_documents_to_create.json = the input documents with the response fields merged in. A failed document fails
the stage (as in PlanExe).
