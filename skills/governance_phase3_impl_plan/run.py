from planexe_skill.shared.governance import run_phase


def to_markdown(r: dict) -> str:
    rows = []
    for i, item in enumerate(r["governance_implementation_plan"], 1):
        if i > 1:
            rows.append("")
        rows.append(f"### {i}. {item['step_description']}")
        rows.append(f"\n**Responsible Body/Role:** {item['responsible_body_or_role']}")
        rows.append(f"\n**Suggested Timeframe:** {item['suggested_timeframe']}")
        rows.append("\n**Key Outputs/Deliverables:**\n")
        for output in item["key_outputs_deliverables"]:
            rows.append(f"- {output}")
        rows.append("\n**Dependencies:**\n")
        for dependency in item["dependencies"]:
            rows.append(f"- {dependency}")
    return "\n".join(rows)


def run(ctx):
    run_phase(ctx, "governance_phase3_impl_plan", [
        ("project-plan.json", "project_plan_raw.json", "json"),
        ("governance-phase2-bodies.json", "governance_phase2_bodies_raw.json", "json"),
    ], to_markdown)
