---
name: classify_domain
description: Identify the expert disciplines the project involves, then pick a primary domain and up to 3 secondaries.
inputs: [plan.txt, identify_purpose_raw.json, identify_purpose.md, extract_constraints.md]
outputs: [classify_domain_raw.json, classify_domain.md]
tier: high
fact_check: false
est_llm_calls: 4
---
Two passes.

1. Candidate generation: up to 3 batched calls (system prompt `prompts/system_<purpose>.md`, schema
   `schema_fits.json`), 3 candidates per batch, until 9 distinct candidates. User message = plan.txt +
   "Plan purpose" + "Extracted constraints" sections. Cleanup in code: normalize labels, drop
   purpose-tag labels (business/public_good/personal/other), duplicates and 1x1 (importance=1, specificity=1) fits,
   clamp Likert scores to 1..5. An empty first batch means the prompt is too vague -> "Unclear".
2. Primary selection: one call (`prompts/primary_select.md`, `schema_primary.json`) choosing the index
   of the primary candidate. Falls back to a deterministic ranking on failure.

Secondaries = first 3 other candidates in document order.
