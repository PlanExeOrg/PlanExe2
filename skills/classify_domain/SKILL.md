---
name: classify_domain
description: Identify the expert disciplines the project involves, then pick a primary domain and up to 3 secondaries.
inputs: [plan.txt, identify_purpose_raw.json, identify_purpose.md, extract_constraints.md]
outputs: [classify_domain_raw.json, classify_domain.md]
uses: [planexe_skill/shared/purpose.py]
tier: high
fact_check: false
est_llm_calls: 4
---
Two passes.

1. Candidate generation: up to 3 batched calls (system prompt `prompts/system_<variant>.md`, schema
   `schema_fits.json`), 3 candidates per batch, until 9 distinct candidates. Domain labels are specific
   noun phrases (2-6 words, one discipline each), qualified by setting or population when that sets the practice apart. User message = plan.txt +
   "Plan purpose" + "Extracted constraints" sections. Cleanup in code: normalize labels, drop
   labels that are purpose tags rather than disciplines (business, business_for_profit, business_non_profit,
   business_other, personal, other, for-profit, non-profit), duplicates and 1x1 (importance=1, specificity=1) fits,
   clamp Likert scores to 1..5. An empty first batch means the prompt is too vague -> "Unclear".
2. Primary selection: one call (`prompts/primary_select.md`, `schema_primary.json`) choosing the index
   of the primary candidate and up to 3 secondary indices. Falls back to a deterministic ranking on failure.

Secondaries = the selection call's picks, topped up (or replaced on failure) by the remaining candidates ranked
by importance × specificity, then specificity, then importance.
