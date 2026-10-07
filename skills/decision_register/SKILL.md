---
name: decision_register
description: Turn the decisions the plan cannot make by itself into a register a human can act on (options, downstream consequences, owner, decide-by month), and list the strategic choices the generator made on the user's behalf for ratification.
inputs: [plan.txt, canonical_facts.json, consistency_recheck_raw.json, candidate_scenarios.json, selected_scenario.json, governance_phase4_decision_escalation_matrix.md]
outputs: [decision_register_raw.json, decision_register.md]
tier: mid
fact_check: false
max_words_per_field: 70
max_items_per_list: 10
est_llm_calls: 1
---
Not part of the original PlanExe pipeline. Added after a Codex comparison of v1 and v2 reports:
"PlanExe v1: generate an unusually comprehensive expert planning workshop. PlanExe v2: construct a
partially validated model of the project, then expose what humans still have to decide." Before this
stage, the open decisions were a one-line banner plus lint diagnostics tagged "needs a project decision".

One call reads the final consistency check (decision kernel + contradictions marked `needs_decision`),
the canonical facts (values marked OPEN), the selected scenario and its rejected alternatives, and the
decision/escalation matrix (who may decide what). It returns:

- `decisions`: each open decision as a question with 2-4 options; for each option, what changes
  downstream (budget, schedule in Month N, gates, scope) and which canonical facts or documents would
  change; the default if nobody decides; owner; decide-by month; what it blocks. Only decisions that the
  inputs show are open: it must not invent new ones or pick an answer.
- `ratify`: the strategic choices the generator made for the user (the chosen scenario's lever
  settings), each with the strongest rejected alternative and when to revisit it.

The candidate open items are enumerated deterministically first (needs_decision contradictions as C1,
C2, ...; OPEN canonical facts as F1, or F1a, F1b, ... when one fact lists several items separated by ';')
and given to the model with ids; each decision names the ids it `covers`. A first version without
this merged unrelated decisions ("breach reserve size and indexing") and dropped one (host identity).
Candidates no decision covers are listed under "Also open" in the markdown (`uncovered_candidates`
in the raw JSON), so nothing is dropped silently.

The report shows this as "Decisions Required", right after the Decision Dashboard. The "Decisions
required" banner counts these decisions.
