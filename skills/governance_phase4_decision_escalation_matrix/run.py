from planexe_skill.shared.governance import run_phase


def to_markdown(r: dict) -> str:
    rows = []
    for i, item in enumerate(r["decision_escalation_matrix"], 1):
        if i > 1:
            rows.append("")
        rows.append(f"**{item['issue_type']}**")
        rows.append(f"Escalation Level: {item['escalation_level']}")
        rows.append(f"Approval Process: {item['approval_process']}")
        rows.append(f"Rationale: {item['rationale']}")
        rows.append(f"Negative Consequences: {item['negative_consequences']}")
    return "\n".join(rows)


def run(ctx):
    run_phase(ctx, "governance_phase4_decision_escalation_matrix", [
        ("project-plan.json", "project_plan_raw.json", "json"),
        ("governance-phase2-bodies.json", "governance_phase2_bodies_raw.json", "json"),
        ("governance-phase3-impl-plan.json", "governance_phase3_impl_plan_raw.json", "json"),
    ], to_markdown)
