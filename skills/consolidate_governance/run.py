SECTIONS = [
    ("Governance Audit", "governance_phase1_audit.md"),
    ("Internal Governance Bodies", "governance_phase2_bodies.md"),
    ("Governance Implementation Plan", "governance_phase3_impl_plan.md"),
    ("Decision Escalation Matrix", "governance_phase4_decision_escalation_matrix.md"),
    ("Monitoring Progress", "governance_phase5_monitoring_progress.md"),
    ("Governance Extra", "governance_phase6_extra.md"),
]


def run(ctx):
    parts = [f"# {title}\n\n{ctx.read_text(name)}" for title, name in SECTIONS]
    ctx.write_text("consolidate_governance.md", "\n\n".join(parts))
