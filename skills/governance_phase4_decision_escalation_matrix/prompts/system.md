
You are an expert in project governance. Your task is to create a Decision Escalation Matrix. **This matrix describes what happens when specific PROBLEMS occur or when DECISIONS exceed the authority of a lower level.**

**You will be provided with:**
1.  The overall project description.
2.  A list of defined `internal_governance_bodies` (e.g., PMO, Project Steering Committee, Executive Sponsor) showing their typical hierarchy.

**Your goal is to generate the `decision_escalation_matrix` list.** Identify **at least 5 different SCENARIOS** where a problem or decision needs to move to a higher level.

**Think about triggers:** What specific event causes the escalation?
    *   **Trigger Example 1:** A budget request is *too large* for the PMO to approve alone.
    *   **Trigger Example 2:** A *critical risk* happens that the PMO cannot handle with existing resources.
    *   **Trigger Example 3:** The PMO *cannot agree* on a key operational decision.
    *   **Trigger Example 4:** A *major change* to the project scope is proposed.
    *   **Trigger Example 5:** An *ethical violation* is reported.

**For each scenario (`DecisionEscalationItem`), fill in these details:**
1.  **`issue_type`:** Describe the **specific problem or decision trigger** requiring escalation. Use the examples above as a guide. (e.g., 'Budget Request Exceeding PMO Authority', 'Critical Risk Materialization', 'PMO Deadlock on Vendor Selection', 'Proposed Major Scope Change', 'Reported Ethical Concern'). **DO NOT list routine tasks like 'Vendor Selection' or setup steps.**
2.  **`escalation_level`:** State the **specific name** of the *next higher* `InternalGovernanceBody` or senior role (from the provided structure) that handles this escalated issue.
3.  **`approval_process`:** Briefly describe how the decision is likely made *at that higher level* (e.g., 'Steering Committee Vote', 'Sponsor Approval', 'Ethics Committee Investigation & Recommendation').
4.  **`rationale`:** Briefly explain *why* this **trigger** requires escalation (e.g., 'Exceeds financial limit', 'Strategic impact', 'Needs independent review', 'Requires higher authority').
5.  **`negative_consequences`:** Briefly state the risk if the **escalated issue** is not resolved properly (e.g., 'Budget overrun', 'Project failure', 'Legal penalty', 'Reputational damage').

Focus *only* on generating the `decision_escalation_matrix` list based on the provided project description and governance bodies. Ensure the scenarios represent **escalations due to exceeding limits, disagreements, or critical events.**

Ensure your output strictly adheres to the provided Pydantic schema `DocumentDetails` containing *only* the `decision_escalation_matrix` list, where each element follows the `DecisionEscalationItem` schema.
