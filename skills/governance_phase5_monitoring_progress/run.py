from planexe_skill.shared.governance import run_phase


def to_markdown(r: dict) -> str:
    rows = []
    for i, item in enumerate(r["monitoring_progress"], 1):
        if i > 1:
            rows.append("")
        rows.append(f"### {i}. {item['approach']}")
        rows.append("**Monitoring Tools/Platforms:**\n")
        for monitoring_tool_platform in item["monitoring_tools_platforms"]:
            rows.append(f"  - {monitoring_tool_platform}")
        rows.append(f"\n**Frequency:** {item['frequency']}")
        rows.append(f"\n**Responsible Role:** {item['responsible_role']}")
        rows.append(f"\n**Adaptation Process:** {item['adaptation_process']}")
        rows.append(f"\n**Adaptation Trigger:** {item['adaptation_trigger']}")
    return "\n".join(rows)


def run(ctx):
    run_phase(ctx, "governance_phase5_monitoring_progress", [
        ("project-plan.json", "project_plan_raw.json", "json"),
        ("governance-phase2-bodies.json", "governance_phase2_bodies_raw.json", "json"),
        ("governance-phase3-impl-plan.json", "governance_phase3_impl_plan_raw.json", "json"),
        ("governance-phase4-decision-escalation-matrix.json",
         "governance_phase4_decision_escalation_matrix_raw.json", "json"),
    ], to_markdown)
