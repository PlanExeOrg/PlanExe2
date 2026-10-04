from planexe_skill.shared.governance import run_phase


def to_markdown(r: dict) -> str:
    rows = []
    rows.append("## Governance Validation Checks")
    for i, item in enumerate(r["governance_validation_checks"], 1):
        if i == 1:
            rows.append("")
        rows.append(f"{i}. {item}")
    rows.append("\n## Tough Questions")
    for i, question in enumerate(r["tough_questions"], 1):
        if i == 1:
            rows.append("")
        rows.append(f"{i}. {question}")
    rows.append(f"\n## Summary\n\n{r['summary']}")
    return "\n".join(rows)


def run(ctx):
    run_phase(ctx, "governance_phase6_extra", [
        ("project-plan.json", "project_plan_raw.json", "json"),
        ("governance-phase1-audit.json", "governance_phase1_audit_raw.json", "json"),
        ("governance-phase2-bodies.json", "governance_phase2_bodies_raw.json", "json"),
        ("governance-phase3-impl-plan.json", "governance_phase3_impl_plan_raw.json", "json"),
        ("governance-phase4-decision-escalation-matrix.json",
         "governance_phase4_decision_escalation_matrix_raw.json", "json"),
        ("governance-phase5-monitoring-progress.json", "governance_phase5_monitoring_progress_raw.json", "json"),
    ], to_markdown)
