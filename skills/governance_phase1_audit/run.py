from planexe_skill.shared.governance import run_phase


def to_markdown(r: dict) -> str:
    rows = []
    rows.append("\n## Audit - Corruption Risks\n")
    for item in r["corruption_list"]:
        rows.append(f"- {item}")
    rows.append("\n## Audit - Misallocation Risks\n")
    for item in r["misallocation_list"]:
        rows.append(f"- {item}")
    rows.append("\n## Audit - Procedures\n")
    for item in r["audit_procedures"]:
        rows.append(f"- {item}")
    rows.append("\n## Audit - Transparency Measures\n")
    for item in r["transparency_measures"]:
        rows.append(f"- {item}")
    return "\n".join(rows)


def run(ctx):
    run_phase(ctx, "governance_phase1_audit", [("project-plan.md", "project_plan.md", "text")], to_markdown)
