# Escaping Organizational Normal Mode
## Mitigating Short-Term Benefits and Long-Term Costs with AI Coworkers

**Status:** Concept and design principles — not an implementation specification. Section 10 lists concrete, testable changes for PlanExe.  
**Scope:** Domain-independent organizations, projects, and operations; and what PlanExe can do about the pattern at planning time  
**Central question:** How can an organization recognize accumulated dysfunction that it regards as normal, and gradually improve its long-term trajectory without reproducing the same incentive failures in AI?

## Executive summary

Many organizations do not experience their harmful decisions as recognizable failures. Instead, the consequences become **normal operating costs**: slow delivery, recurring defects, inaccessible services, security exposure, high maintenance effort, staff frustration, or repeated reorganizations. Management may continue to see successful projects, profitable operations, and acceptable internal KPIs.

A recurring mechanism is **short-term benefit / long-term cost transfer**:

1. A decision produces a measurable short-term gain: lower budget, earlier delivery, attractive status report, or career reward.
2. The decision defers cost, risk, complexity, or harm to future teams, customers, or society.
3. The people receiving credit are not necessarily the people who later bear the consequences.
4. Staff with relevant expertise may warn about the trade-off, but those warnings are filtered, discounted, or repeatedly deprioritized.
5. Subsequent costs are treated as ordinary operations rather than traced back to the decisions that created them.
6. The organization adapts to the degraded baseline and loses sight of the counterfactual: what could performance have been under different decisions?

The proposed intervention is a network of **AI coworkers at every organizational level, including management**, connected through a governed **shared evidence ledger** (shared organizational memory, **not enforced consensus**). Their work is to observe, probe, propose small improvements, test outcomes, preserve disagreements, and route important findings to people who can act on them.

Three distinct problems keep the pattern in place, and solving one does not solve the others:

| Problem | Mechanism |
|---|---|
| The organization cannot see its dysfunction | AI coworkers investigate the current state and compare credible alternatives |
| Inconvenient findings do not reach decision-makers | Shared evidence and independent escalation |
| The incentives favour the short-term choice | Long-term accountability and incentive reform |

The third is likely the hardest: a manager can fully understand a finding and still rationally choose the short-term saving.

**Core principle:** Optimize for the organization's long-term outcomes, not simply the apparent success of the current project or the reward horizon of its manager.

---

## 1. The failure mode: dysfunction as the baseline

The common story says: a project makes a bad choice, it fails, and the organization learns from the failure.

The more difficult case is different:

- Nothing obviously collapses.
- Chronic rework, security gaps, and inefficient coordination become standard practice.
- Budgeting and delivery forecasts incorporate the inefficiency as though it were unavoidable.
- The organization measures performance relative to its own degraded history.
- No postmortem connects long-term costs to the decisions that created them.
- People who warned about the problems leave, adapt, or are discounted.

**The organization may not recognize a failure because it has no credible comparison with a better state.** Remaining profitable does not demonstrate operational efficiency, fairness, resilience, or the absence of avoidable harm.

### Common cross-domain patterns

| Pattern | Immediate benefit | Hidden or delayed cost | Why the organization may not notice |
|---|---|---|---|
| Security postponed | Earlier release; smaller initial budget | Vulnerability accumulation, incidents, costly remediation | Risk remains latent until an incident; security work is invisible when successful |
| Automated testing omitted | More apparent feature velocity | Regressions, manual verification, slower change, rising maintenance cost | Rework is classified as ordinary development |
| Accessibility ignored | Less initial design and testing | Excluded users, retrofit cost, legal exposure, lost opportunity | Missing users rarely appear in customer feedback |
| Junior staffing substituted for needed expertise | Lower visible labor rate | Mentoring bottlenecks, architectural errors, rework, longer schedules | Headcount cost is measured; total delivery cost is not |
| Developer advice discounted | Fewer immediate objections; faster approval | Known risks materialize later | Warnings are not captured alongside the decision |
| Polished consultant preferred over substantive expertise | Reassuring presentations and management alignment | Incorrect confidence; weak technical decisions | Persuasiveness is mistaken for evidence |
| Rivalry over funding | A manager or department protects its allocation | Duplicated work, obstruction, distorted reporting | Competition is interpreted as normal politics |
| Trivial work and recurring meetings | Visible activity and procedural compliance | Opportunity cost; decisions and delivery are delayed | Meeting count and document volume substitute for outcomes |
| Deferred maintenance | Favorable current-year results | Large future replacement or operating costs | Costs occur under a different budget owner or management team |

These are **failure hypotheses**, not automatic diagnoses. Poor outcomes can also result from genuine resource scarcity, uncertainty, legitimate trade-offs, or incorrect technical advice. The system must investigate rather than assume bad faith.

## 2. What makes the pattern persistent?

### 2.1 Different benefit and liability horizons

A decision-maker might receive credit this quarter, while the costs arise five or ten years later. Promotion, transfers, outsourcing, and reorganization can break the link between the original decision and its consequences.

**Questions to ask of important decisions:**

- Who gets the near-term benefit?
- Who pays or is harmed later?
- When do benefits appear, and when can costs appear?
- Will the original decision-maker still own the outcome?
- Is the decision reversible? At what cost?

### 2.2 Filtering expertise through the hierarchy

A specialist may accurately identify a risk while lacking access, status, or a vocabulary that management recognizes. A consultant who confidently uses management language may be more persuasive, even if their recommendation has weaker evidence.

The problem is not that management-oriented communication is bad. It is that **presentation and organizational status can overwhelm the merits of the argument**.

### 2.3 Missing feedback and missing counterfactuals

Organizations know what they spent, but often not what avoidable rework cost them. They know how fast a release shipped, but not how much future change became harder. They know how many users are active, but not who cannot use the service at all.

A meaningful baseline should include outcome quality, harm, opportunity costs, and future liabilities — not just schedule and expenditure.

### 2.4 Success metrics reward local optimization

A project can meet schedule, budget, and scope while damaging long-term organizational value. Department-level optimization can worsen organization-wide outcomes. A risk accepted by one team can become an unfunded obligation for another.

### 2.5 Information can be inconvenient to powerful people

A warning may challenge the plan on which someone's reputation, promotion, or budget depends. This creates incentives to minimize, delay, reframe, or suppress it — without requiring anyone to be consciously malicious.

---

## 3. A general-purpose mitigation strategy

Do not attempt to fix organizational behavior by adding more mandatory reports. Instead, strengthen the **feedback paths, incentives, and decision records** around consequential choices.

### 3.1 Track decisions over their full economic and human lifetime

For major decisions, keep a concise, durable record:

- **Decision:** What was chosen?
- **Alternatives:** What other choices were considered?
- **Evidence:** What facts, estimates, and uncertainties supported the choice?
- **Warnings and dissent:** What material objections were raised, by whom or by which role, and how were they answered?
- **Ownership:** Who authorized the decision and who will carry its future liabilities?
- **Time horizons:** Effects expected in weeks, quarters, years, and beyond.
- **Revisit trigger:** What observation would justify reversing the decision?
- **Outcome:** What actually happened, including after ownership changes?

Preserve the history even when the organization restructures. Record decisions, not speculative judgments about personal motives.

### 3.2 Evaluate the cost of inaction — and the cost of the quick win

Every significant proposed saving should have a corresponding **deferred-cost assessment**:

| Dimension | Questions |
|---|---|
| Immediate benefit | How much time or expenditure is saved, and for whom? |
| Future cost | What maintenance, rework, incident exposure, or replacement cost is shifted forward? |
| Affected parties | Who bears the cost, including users who have no voice in the project? |
| Uncertainty | Which estimates are measured, inferred, or unknown? |
| Irreversibility | How expensive will it be to change course later? |
| Ownership | Who funds remediation if the risk materializes? |
| Review | What evidence and date should trigger reassessment? |

Use ranges and scenarios instead of invented precision. Costs that are not yet known should remain explicitly **unknown**, not silently set to zero.

### 3.3 Treat expert warnings as evidence, not vetoes or nuisances

- Offer a low-friction channel for concrete technical and operational concerns.
- Require a reasoned disposition for material warnings: **accepted, mitigated, rejected with rationale, or unresolved**.
- Separate **factual disagreement** from **risk acceptance**. A manager can sometimes accept a risk; that does not make the risk false.
- Route issues to the appropriate authority when they exceed the current owner's mandate.
- Allow documented corrections when a warning turns out to be mistaken.

Avoid creating a bureaucratic requirement to escalate every objection. Escalate based on severity, evidence, urgency, and affected parties.

### 3.4 Protect non-negotiable quality and safety boundaries

Security, accessibility, safety, privacy, and regulatory obligations cannot always be treated as optional feature priorities. Define applicable minimum standards and acceptance criteria early. If exceptions are permitted, require appropriate authorization, compensating controls, expiry dates, and a remediation owner.

Not every minimum is universal. Distinguish:

- **Binding legal and regulatory requirements**, which depend on jurisdiction.
- **The organization's own commitments** (published policies, contracts, stated standards).
- **Domain-specific safety requirements**, established by engineering or professional analysis for that domain.
- **Optional improvements** beyond those minimums, which are legitimate trade-offs.

The first three come from the context (jurisdiction, policy, domain), not from a universal threshold the analysis invents. Within them, these minimums are **constraints, not objectives to trade away**. An analysis may report that a plan breaches one, or what meeting it costs, but it never offers dropping it as a saving: "cut accessibility work and save 20%" is a breach to flag, not an option to weigh.

Automated testing levels and architectural investments, by contrast, usually require context-sensitive engineering choices. Do not turn one good practice into an inflexible universal rule.

### 3.5 Realign incentives with outcomes

Useful options include:

- Evaluate investments using **lifecycle cost**, not only launch cost.
- Add quality, reliability, accessibility, maintenance burden, and realized customer outcomes to success reviews.
- Track remediation obligations across budget cycles and manager transitions.
- Make accepted long-term risks visible to successor owners.
- Reward early discovery and correction of bad assumptions, not just optimistic reporting.
- Run retrospective reviews of previous decisions without using the exercise as a mechanism for personal retaliation.

Incentives should avoid simplistic scores that employees can game. Use a small, balanced set of signals and qualitative review.

**Better knowledge is not better incentives.** If a manager's bonus depends on staying within the annual budget, a well-evidenced finding that cutting maintenance creates expensive liabilities may change nothing: the manager understands it and still rationally takes the saving. Detection only helps if governance changes the payoff:

- **Assign long-term liabilities an owner** at decision time, and keep that ownership attached when people move on.
- **Carry remediation budgets across management transitions** instead of letting them lapse with the annual cycle.
- **Evaluate consequential decisions beyond the annual cycle**, e.g. by reviewing them again after two to five years against the predictions made at the time.

AI coworkers can expose the trade-off; only governance can make the long-term choice the rewarded one.

### 3.6 Use modest, reversible interventions

Prefer targeted interventions with a measurable hypothesis:

> **Hypothesis:** Adding automated regression coverage around the five most failure-prone modules will reduce repeat defects and release verification effort without unacceptable maintenance overhead.
>
> **Test:** Compare defect recurrence and engineering time before and after the change, accounting for release volume and complexity.
>
> **Decision:** Expand, modify, or discontinue based on results.

This is more credible than assuming the entire organization must immediately adopt a predetermined “best practice.”

---

## 4. AI coworkers and a shared evidence ledger

### 4.1 Place AI coworkers in management as well as delivery teams

Embedding AI only with developers reproduces the old escalation problem: useful insights can be filtered by the same hierarchy that previously ignored them.

| Placement | Questions an AI coworker can help examine |
|---|---|
| Individual contributors | Where does rework originate? Which warnings recur? Which tools or dependencies waste time? |
| Team leads | What is blocking delivery? Is skill mix adequate? Where are interruptions and quality problems created? |
| Project managers | Which assumptions are untested? Are schedules, decisions, and risks consistent? What is being deferred? |
| Department management | Are incentives and budgets creating systemic bottlenecks? Are problems repeated across teams? |
| Executive management | Which apparent quick wins create long-term liabilities? Which strategic claims lack evidence? |
| Independent assurance functions | Are legal, security, accessibility, privacy, or safety boundaries being bypassed? |

**The AI in management must be able to receive well-supported findings from lower levels** without relying entirely on a single human manager to forward them.

### 4.2 Shared evidence, not a compulsory shared opinion

Agents share one organizational evidence ledger, while reasoning independently and free to disagree.

A useful minimum information model:

- **Observation:** What happened? Source, timestamp, access classification.
- **Hypothesis:** Proposed explanation, competing explanations, confidence and gaps.
- **Decision:** Options, selection, owner, rationale, predicted outcomes.
- **Dependency:** What other work, teams, or assumptions does this depend on?
- **Risk:** Who is exposed, severity, uncertainty, mitigation, escalation threshold.
- **Experiment:** Intervention, baseline, success criteria, results.
- **Outcome:** Observed effects at short and long time horizons.
- **Dissent:** Alternative assessments that should remain visible rather than being averaged away.

Agents should retrieve the same underlying evidence, **not merely repeat one another's summaries**. Contradictory interpretations must remain inspectable.

### 4.3 Escalation by evidence and impact

A possible routing protocol:

1. A developer-side agent notices recurring regressions in a module.
2. It links defects, remediation effort, and release records to form a testable hypothesis.
3. The team-level agent checks alternative causes and proposes a small testing intervention.
4. The project-management agent evaluates budget and schedule implications.
5. If the issue remains unresolved and exceeds an agreed threshold, a management-level agent receives an evidence-backed summary **and the dissent**.
6. A human authority makes the decision, and the result is recorded.
7. Agents follow up to see whether the expected benefits or costs appeared.

Escalation must be **traceable, bounded, and contestable**. It should not become unlimited upward reporting of private conversations or unverified accusations.

### 4.4 Separate three roles

- **Observer:** Gathers permitted operational evidence and identifies anomalies.
- **Challenger:** Tests assumptions, searches for disconfirming evidence, examines incentives and unintended consequences.
- **Planner / experiment designer:** Produces options, predicts trade-offs, and helps people carry out approved, measurable improvements.

These can be agent roles rather than separate models. Important decisions benefit from independent review, because fully synchronized agents can amplify the same mistake across the whole organization.

### 4.5 Avoid recreating organizational dysfunction in AI

Potential failure modes and safeguards:

| AI failure | Safeguard |
|---|---|
| Becomes a management surveillance system | Data minimization, purpose limits, role-based access, worker involvement, privacy review, compliance with employee-monitoring and labour law (e.g., works-council consultation and GDPR in the EU) |
| Repeats the opinion of the highest-status agent | Evidence-backed dissent, independent challenge, explicit uncertainty |
| Generates convincing but unverified management language | Provenance labels, verification gates, clear separation of observation and speculation |
| Produces more meetings and reports | Measure reduction in wasted work; require decisions or useful learning from outputs |
| Optimizes the wrong KPI | Balanced outcomes across time horizons and stakeholder groups |
| Prices legal, safety or ethical minimums as savings | Treat them as constraints the optimization must respect (§3.4); flag breaches, never propose them as options |
| Makes unsupported accusations about individuals | Focus on decisions, process and evidence; right to contest and correct |
| Quietly makes consequential organizational changes | Human authorization, audit trail, reversibility, rollback criteria |
| Concentrates sensitive organizational knowledge | Least privilege, compartmentalized access, retention limits, security controls |
| Treats a local improvement as overall progress | Evaluate spillovers and externalized costs across the organization |

### 4.6 Governance and independence

The system's central weakness is that the agents meant to surface inconvenient findings about management are usually deployed, configured, and funded by management. This is a design requirement, not an open question:

- **Independent reporting line.** Findings above an agreed severity go to a body that does not depend on the manager concerned: internal audit, an assurance function, a board committee, or an equivalent.
- **Two stores with different rules.** An **audit trail** of decisions, dispositions, and changes is append-only and versioned, so deleting or reclassifying a finding leaves a trace. The **underlying evidence** (documents, records, statements, personal data) has retention, redaction, correction, and access-control policies, because an immutable store of sensitive employee information becomes a liability over decades. The audit trail records that evidence was redacted or deleted, and why, without keeping its content.
- **Configuration under shared control.** Changes to what agents may observe, how they escalate, or what they suppress require approval by more than the line management they report on.
- **Resistance to manipulation.** Expect people to steer the agents: feeding selective evidence, framing questions, or flooding the ledger. Agents check whether evidence is complete (what is missing from the record, not only what is in it) and record who supplied each item.

The ledger cannot force anyone to act on a finding. What it can do is make inaction a recorded decision: a finding above the severity threshold is closed only by a named authority choosing a disposition (accepted risk, mitigated, rejected with rationale), and that record stays visible to successor owners and to the independent reporting line. That is the realistic lever.

The hardest step is not technical. It is getting an organization to accept, and keep funding, a system able to challenge its established practices. Adoption needs a sponsor whose own incentives favour long-term outcomes (a board, a regulator, a funder, or an owner), and it should start where that sponsor has authority (§6, Phase A).

### 4.7 Evidence standard for root-cause claims

Linking defect histories, budgets, and decisions into a causal chain is where AI is most likely to produce plausible but false explanations. Before a root-cause claim is escalated:

- Every link in the chain cites its sources, and each link is labelled **measured**, **inferred**, or **assumed**.
- At least one competing explanation is stated, with the evidence that distinguishes it.
- Numbers are recomputed by code, not restated by the model.
- A claim about a person's or team's decision is shown to them before it goes upward, with a **time-limited right to respond** whose length depends on severity and urgency (e.g., 5 working days for an ordinary organizational concern). Their response is attached to the claim; it does not block escalation. If they dispute the claim, escalation proceeds with both versions and the disagreement is recorded as dissent. For a critical or imminent risk (a security vulnerability, a safety incident), protective escalation happens immediately and the response is attached afterwards.

Insufficient evidence lowers confidence; it does not by itself prevent escalation, especially when the evidence needed to verify a claim is controlled by the people it concerns:

| Category | Escalation |
|---|---|
| Verified finding | Normal escalation |
| Unverified but potentially severe risk | Provisional escalation, clearly labelled as unverified, with what would verify it |
| Weak hypothesis with limited impact | Kept in the ledger for investigation |

---

## 5. How to find the “normal” problems

The system needs ways to detect problems that lack incident tickets, executive complaints, or obvious failures.

### 5.1 Probe the baseline from several angles

- **Flow:** Where do items repeatedly wait, get reworked, or require approval?
- **Quality:** Which defects recur? Which users or conditions are missing from tests?
- **Experience:** Which accessibility barriers or customer needs remain unmeasured?
- **Expertise:** Which warnings were raised and subsequently discounted?
- **Resources:** Where do inexpensive staffing decisions produce expensive coordination?
- **Incentives:** What behavior do budgets and performance reviews actually reward?
- **Time horizon:** Which costs lie beyond the current project or management tenure?
- **Organizational boundaries:** Where does one team's apparent saving increase another team's workload?
- **Counterfactuals:** What would a credible alternative process, tool, or design achieve?

### 5.2 Triangulate evidence

No single data source describes organizational reality. Combine, where authorized:

- Work and defect histories.
- Incidents, security findings, and accessibility evaluations.
- Engineering and operational time allocations, preferably aggregated.
- Budget changes, investment cases, and ownership transitions.
- Decision records, documented warnings, and customer feedback.
- Interviews and voluntary, confidential worker input.
- Carefully selected external benchmarks or controlled internal comparisons.

**Avoid treating communication metadata or employee behavior analytics as a shortcut to understanding people.** The purpose is to improve the system, not to infer disloyalty or measure individual productivity through surveillance.

### 5.3 Distinguish symptoms from root causes

Example chain:

> Slow feature delivery → recurring regressions → insufficient automated regression coverage → testing repeatedly deferred → project rewarded for launch speed, not maintenance burden.

The correct intervention might involve tests, but the **root organizational fix** may be changing budget and delivery incentives. Merely telling developers to “write more tests” can leave the underlying problem untouched.

---

## 6. An incremental adoption path

The practical objective is to establish a trustworthy improvement loop, not to deploy omniscient agents overnight.

### Phase A — Baseline and consent

Choose one willing organizational unit and two or three observable problems. Define the permitted data, worker protections, decision rights, success criteria, and what AI will **not** do. Start with existing records and voluntary input rather than indiscriminate monitoring.

### Phase B — Evidence and memory

Create a lightweight decision/evidence ledger. Reconstruct a few significant past decisions and their current consequences. Check whether the reconstructed history is correct with the people involved. Label unknowns and disputes.

### Phase C — Controlled improvement experiments

Run small, reversible interventions (for example, regression tests around a failure-prone component, a shorter approval path, or an accessibility audit and remediation pilot). Compare outcomes against credible baselines, including adverse effects.

### Phase D — Management integration

Add AI coworkers supporting project and department management. Define severity-based routes that carry evidence and dissent between levels. Ensure that management sees the long-term cost of apparently attractive shortcuts, while protecting confidential information and legitimate decision authority.

### Phase E — Cross-team learning

Use the shared evidence system to recognize recurring failure structures across projects. Compare the results of similar interventions. Continue independent challenge and check for organization-wide side effects.

### Phase F — Longitudinal accountability

Revisit predictions over years, including after managers or teams change. Track whether deferred costs materialized, whether risks were mitigated, and whether the organization improved against an external or experimentally supported counterfactual.

Do not automatically expand deployment unless there is evidence of benefit and organizational trust.

---

## 7. How to measure whether this is working

A system aimed at long-term improvement needs more than adoption metrics and AI-generated recommendations.

| Dimension | Illustrative indicators | Watch out for |
|---|---|---|
| Delivery | Lead time, blocked time, completed value | Faster output that increases future rework |
| Software quality | Escaped defects, repeat failures, regression effort | Fewer reported bugs because reporting is discouraged |
| Security | Remediation age, verified control coverage, material exposure | Counting findings without considering severity |
| Accessibility | Independent task-completion tests with affected users | Treating automated scans as proof of accessibility |
| Maintainability | Change effort, dependency fragility, rework trends | Reducing investment in ways that hide future cost |
| Organizational learning | Predictions revisited, issues resolved, corrections made | Incentivizing large quantities of trivial “findings” |
| Decision quality | Evidence quality, acknowledged dissent, reversibility | Compliance theater; records without better decisions |
| Long-term value | Lifecycle cost, avoided loss, user outcomes, resilience | Assuming an unmeasured counterfactual is proven |
| Trust and safety | Worker feedback, appeal outcomes, privacy incidents | Productivity gains achieved through coercive monitoring |

Where possible, use matched comparisons or phased rollout to estimate impact. Attribute benefits cautiously; organizational outcomes have many causes.

### Success is *not*

- Number of AI coworkers deployed.
- Number of warnings, slides, or reports generated.
- Number of managers “caught” making mistakes.
- Universal agreement among the agents.
- Maximizing a single short-term financial KPI.

**Success is a demonstrable improvement in decisions and outcomes that persists beyond the next reporting cycle.**

---

## 8. Strategic design principles

1. **Treat "normal" as a hypothesis, not a benchmark of adequacy:** start from observed reality and credible counterfactuals.
2. **Make deferred costs and risk transfers visible,** including those that fall after the original owners have moved on.
3. **Protect the route from domain expertise to decision authority,** which is why AI coworkers belong in management too.
4. **Share evidence, not opinions:** preserve independent reasoning and dissent.
5. **Prefer small, reversible, measured improvements,** and measure whether the improvement system itself creates waste or harm.
6. **Preserve human agency, due process, privacy, and accountability.**

## 9. Open research and design questions

- How can agents estimate **counterfactual performance** when the organization has never operated differently?
- How should long-term costs be valued when effects appear years later or fall on users outside the organization?
- What escalation rules reliably surface serious problems without creating a torrent of low-value alerts?
- How can the system tell a legitimate disagreement from a suppressed warning without making claims about motives?
- Can independent agents preserve meaningful dissent while still coordinating on decisions?
- Section 4.6 sets requirements for governance; which concrete reporting lines and controls hold up in practice, in organizations of different size and ownership?
- What prevents the improvement apparatus from becoming another source of bureaucracy, employee surveillance, and short-term KPI gaming?
- How should success be measured when the most valuable outcome is an incident that *didn't* occur or a bad investment that was *never* made?

## 10. What this means for PlanExe

PlanExe works at planning time, before a decision is taken, which is the cheapest point to make a cost transfer visible. It should keep three reasoning tasks apart:

1. **Detect** a possible unfavourable consequence (the critique stages).
2. **Establish how likely** it is, with evidence labelled measured, inferred, or assumed (§4.7).
3. **Decide whether it is acceptable**, which belongs to an authorized person. PlanExe recommends; it does not decide.

Several of the mechanisms above already exist in its pipeline, in a planning-time form:

| This note asks for | PlanExe already has |
|---|---|
| Independent challenge (§4.4, Challenger) | `premise_attack`, `expert_criticism`, `self_audit` |
| Decision records with alternatives, owner and revisit trigger (§3.1) | `decision_register`: `options`, `consequences`, `owner`, `decide_by`; `ratify` with `revisit_by` |
| Deferred costs and long-term liabilities (§3.2) | `self_audit` checks "Lacks Operational Sustainability" and "Underestimating Risks" |
| Unknown costs stay unknown, not zero (§3.2) | canonical facts labelled "(estimate)" and "OPEN decision" |

Plans already find long-term costs, but they end up scattered across sections. Examples from October 2026 runs: Clear English leaves stewardship after Month 36 unfunded, media rescue has a USD 280 M gap between budget and cost, and the rubber programme leaves USD 13.9 B unassigned. Three general changes would make this a consistent output. Each can be tested with single-stage runs on copies of existing plans.

1. **Decision externalities.** For each consequential decision, the plan states the following. This applies in both directions: a shortcut or reserve cut can defer costs, and so can over-investment, e.g. excessive redundancy that locks in long-term cost (`self_audit`'s "Gold Plating" check is the counterpart).

   | Dimension | Question |
   |---|---|
   | Immediate benefits | Who gains, and when? |
   | Deferred costs | Who pays later, and when? |
   | Externalities | Which costs fall outside the project's boundaries (other teams, users, society)? |
   | Time horizon | Do the consequences outlive the project? |
   | Accountability | Who owns the resulting obligations and funds the remedy? |
   | Reversibility | Can the decision be undone, and at what cost? |
   | Counterfactual | What follows from the main alternative? (`decision_register` already holds the options and their consequences.) |
   | Opportunity cost | What valuable work does this prevent from ever happening (e.g., years of maintenance effort that could have built something else)? |

   The minimums of §3.4 are inputs to this analysis, not dimensions to trade. Implement as fields on `decision_register` decisions, or as a `self_audit` check. Test: run the stage on copies of the Clear English, media rescue and heatwave plans and check that the known transfers appear.
2. **Dissent in the decision register.** Each decision records the strongest objection raised against it (from `expert_criticism`, `premise_attack`, or the review stages), with independent fields:

   | Field | Example |
   |---|---|
   | Origin | AI-generated / stakeholder-raised |
   | Evidence status | Unsupported / partly supported / independently verified |
   | Confidence | Low / medium / high |
   | Severity | Low / medium / high / critical |
   | Disposition | Proposed by PlanExe; actual disposition awaiting a human decision |

   Origin and evidence status are separate: an AI objection can be verified, and a human objection can be unsupported. A planning-time report must not invent organizational history, so it separates four things: the **recommended decision** and the **predicted consequences** (which PlanExe produces), and the **actual decision** and the **observed consequences** (which stay unset until an authorized person decides and outcomes are observed). Test: rerun `decision_register` on a copy and check that objections carry their source, and that no actual disposition is filled in.
3. **Effects beyond the plan's horizon.** Plans state the effects and obligations that fall after their own end date (operation, maintenance, renewal, stewardship), with who carries them. This connects to `docs/notes/20261014_timescale.md`: the follow-up phase of a short-horizon plan and the renewal cycles of a long one are both effects beyond the main horizon. Test: check that the Yellowstone and rubber plans list them in one place.

These keep PlanExe general-purpose: none of them depends on a domain, and none adds framing that would bias a plan towards caution. They make visible what a plan already implies.

The predicted and observed consequences of change 2 are also the natural interface to the vision in §4–§7: PlanExe reasons about possible futures, while AI coworkers investigate the present and remember the past. PlanExe's predicted consequences can later be compared with observed ones, closing a learning cycle: observe, plan, predict, decide, measure, update.

Apart from that interface, this section does not depend on §4–§7. The AI-coworker network is a long-term vision; these three changes are contained engineering work on a different timescale, and should be planned and evaluated separately.

## Closing thesis

The central limitation of conventional planning is not always missing knowledge or a poor schedule. Often, organizations **already possess warnings and expertise but have no reliable mechanism for turning them into decisions**, especially when doing so threatens short-term rewards.

A network of AI coworkers could help by providing shared situational awareness, durable institutional memory, independent challenges, and continuous, evidence-based improvement across organizational levels.

**The objective is not to create an organization that never makes mistakes. It is to create one that can recognize the costs it has normalized, learn from inconvenient evidence, and steadily stop transferring today's benefits into tomorrow's liabilities.**
