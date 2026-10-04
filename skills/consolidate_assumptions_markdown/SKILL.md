---
name: consolidate_assumptions_markdown
description: Merge locations, currency, risks, and assumption stages into one reference document.
inputs: [identify_purpose.md, classify_domain.md, plan_type.md, physical_locations.md, currency_strategy.md, identify_risks.md, make_assumptions.md, distill_assumptions.md, review_assumptions.md]
outputs: [consolidate_assumptions_full.md, consolidate_assumptions_short.md]
tier: low
est_llm_calls: 9
parallel_llm: 9
---
Nine upstream markdown documents (Purpose, Domain, Plan Type, Physical Locations, Currency Strategy,
Identify Risks, Make Assumptions, Distill Assumptions, Review Assumptions), in that order.

- Full (deterministic): `# <Title>\n\n<content>` per document, joined with blank lines.
- Short: each document is shortened by one plain-text LLM call (`prompts/shorten_markdown.md`;
  input stripped and bold removed; output taken between `[START_MARKDOWN]`/`[END_MARKDOWN]`, bullet
  lists padded with blank lines, bold removed) and emitted as `# <Title>\n<short>`. A failed call
  yields a "**Problem with document:**" chunk instead (as in PlanExe). The calls are independent and
  run concurrently.

Prompt tweak vs PlanExe: two lines added to the shorten prompt — keep the wording and level of
existing '#'/'##' headings, and turn section label lines ("Rationale: ...") into '##' headings.
Sonnet otherwise renamed/promoted headings (e.g. "## Location 1" -> "# Location 1: <place>").
