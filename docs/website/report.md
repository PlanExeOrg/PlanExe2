---
title: The report
---

# The report

A finished run produces `report.html` (and the same content as `report.md`) in its run directory. The report
leads with the decisions and key facts, not the workshop. It has three parts.

## Part 1: Key decisions and facts

Start here. These sections are what a human has to act on.

| section | what it is for |
|---|---|
| **Decision Dashboard** | The go/no-go gates the plan depends on. |
| **Decisions Required** | Each open decision with its options, downstream consequences, an owner and a decide-by month, ranked by importance. Ends with **Choices made on your behalf**: strategic choices the generator made to complete the plan, for you to ratify or reject. |
| **Canonical Facts** | One table of the key numbers and dates. Every other section is checked against it. |
| **Executive Summary** | Scope, goals, deliverables, timeline, budget and main risks. If this is wrong, the rest will be wrong too. |
| **Gantt** | A draft schedule computed from the estimated durations and dependencies. |

## Part 2: Supporting analysis

PlanExe's planning documents. Use them to understand and challenge the decisions in Part 1.

- **Pitch** and **Project Plan** (SMART criteria, dependencies, resources, stakeholders, regulatory
  requirements).
- **Strategic Decisions** and **Scenarios**: the levers the plan considered and the path it chose.
- **Assumptions**, **Physical Locations**, **Currency Strategy**, **Risks**.
- **Governance**: bodies, implementation plan, escalation matrix, progress monitoring.
- **Data Collection**, **Documents to Create and Find**.
- **SWOT Analysis**, **Team**.
- **Expert Criticism**: the plan reviewed from several specialist viewpoints.
- **Work Breakdown Structure**, **Review Plan**, **Questions & Answers**.
- **Premortem** and **Self Audit**: adversarial sections that assume the plan failed and look for why.

## Part 3: Audit trail

What was checked, and what was not.

| section | what it tells you |
|---|---|
| **Validation Status** | What "validated" means for this report: which sections searched the web, the consistency lint result before and after repair, a deterministic re-computation of every written calculation, and which sections were not checked. |
| **Consistency Check** | The full lint of the core documents against the Canonical Facts. If the lint still fails after repair, the report shows a "Consistency lint FAILED" banner. |
| **Initial Prompt Vetted** | How the prompt was screened before planning. |
| **Prompt Adherence** | Whether the plan kept to what the prompt asked for. |
| **Metadata** | Generator version and commit, and per stage: when it ran, which models it used, LLM calls and web searches, and which files were hand-edited. |

## How to use it

1. Go through **Decisions Required** and **Choices made on your behalf**. Correct anything that doesn't
   match your situation.
2. Check the **Canonical Facts** and **Executive Summary** for scope, budget and timeline.
3. Read **Validation Status** to see which parts are unchecked.
4. Use Part 2 to challenge the plan with stakeholders and domain experts.

To change something, edit the relevant intermediary file in the run directory and re-run; see
[How it works](how_it_works.md#editing-and-re-running).
