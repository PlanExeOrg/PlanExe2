from planexe_skill.shared.governance import run_phase


def to_markdown(r: dict) -> str:
    rows = []
    for i, body in enumerate(r["internal_governance_bodies"], 1):
        rows.append(f"### {i}. {body['name']}")
        rows.append(f"\n**Rationale for Inclusion:** {body['rationale_for_inclusion']}")
        rows.append("\n**Responsibilities:**\n")
        for resp in body["responsibilities"]:
            rows.append(f"- {resp}")
        rows.append("\n**Initial Setup Actions:**\n")
        for action in body["initial_setup_actions"]:
            rows.append(f"- {action}")
        rows.append("\n**Membership:**\n")
        for member in body["membership"]:
            rows.append(f"- {member}")
        rows.append(f"\n**Decision Rights:** {body['decision_rights']}")
        rows.append(f"\n**Decision Mechanism:** {body['decision_mechanism']}")
        rows.append(f"\n**Meeting Cadence:** {body['meeting_cadence']}")
        rows.append("\n**Typical Agenda Items:**\n")
        for item in body["typical_agenda_items"]:
            rows.append(f"- {item}")
        rows.append(f"\n**Escalation Path:** {body['escalation_path']}")
    return "\n".join(rows)


def run(ctx):
    run_phase(ctx, "governance_phase2_bodies", [
        ("project-plan.md", "project_plan.md", "text"),
        ("governance-phase1-audit.md", "governance_phase1_audit.md", "text"),
    ], to_markdown)
