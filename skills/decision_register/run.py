import json

from planexe_skill.planexe import format_json_for_query, raw_document, structured

SEVERITY_ICON = {"high": "🔴 High", "medium": "🟡 Medium"}


def cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def to_markdown(r: dict) -> str:
    decisions = r.get("decisions") or []
    rows = [r.get("summary", ""), ""]
    if decisions:
        rows += ["| # | Decision | Severity | Owner | Decide by | Blocks |", "|---|---|---|---|---|---|"]
        for i, d in enumerate(decisions, start=1):
            rows.append(f"| {i} | {cell(d['title'])} | {SEVERITY_ICON.get(d['severity'], d['severity'])} | "
                        f"{cell(d['owner'])} | {cell(d['decide_by'])} | {cell(d['blocks'])} |")
        rows.append("")
    else:
        rows += ["No open decisions were found: the consistency check found no contradiction that needs a project "
                 "decision, and no canonical fact is marked OPEN.", ""]
    for i, d in enumerate(decisions, start=1):
        rows += [f"## {i}. {d['title']} ({SEVERITY_ICON.get(d['severity'], d['severity'])})", "",
                 f"**Decision:** {d['question']}", "",
                 f"**Why it is open:** {d['why_open']}", "",
                 "| Option | Consequences | What changes in the plan |", "|---|---|---|"]
        for j, o in enumerate(d.get("options") or []):
            rows.append(f"| {chr(65 + j)}. {cell(o['option'])} | {cell(o['consequences'])} | {cell(o['plan_changes'])} |")
        rows += ["", f"- **If nobody decides:** {d['default_if_undecided']}",
                 f"- **Owner:** {d['owner']}",
                 f"- **Decide by:** {d['decide_by']}",
                 f"- **Blocks:** {d['blocks']}", ""]
    ratify = r.get("ratify") or []
    if ratify:
        rows += ["## Choices made on your behalf", "",
                 "The generator picked a scenario and set these levers itself. They are assumptions, not your "
                 "decisions: confirm or change them.", "",
                 "| Lever | Chosen | Strongest alternative | Why it matters | Revisit by |", "|---|---|---|---|---|"]
        for c in ratify:
            rows.append(f"| {cell(c['lever'])} | {cell(c['chosen'])} | {cell(c['main_alternative'])} | "
                        f"{cell(c['why_it_matters'])} | {cell(c['revisit_by'])} |")
    return "\n".join(rows).strip() + "\n"


def run(ctx):
    recheck = ctx.read_json("consistency_recheck_raw.json")
    selected = ctx.read_json("selected_scenario.json")
    sections = [
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}",
        f"File 'consistency_recheck_raw.json' (final consistency check):\n{format_json_for_query(recheck)}",
        f"File 'selected_scenario.json' (final choice):\n{json.dumps(selected.get('final_choice', selected), ensure_ascii=False)}",
        f"File 'candidate_scenarios.json':\n{format_json_for_query(ctx.read_json('candidate_scenarios.json'))}",
        f"File 'governance_phase4_decision_escalation_matrix.md':\n{ctx.read_text('governance_phase4_decision_escalation_matrix.md')}",
    ]
    user_prompt = "\n\n".join(sections)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    ctx.write_json("decision_register_raw.json", raw_document(response, result, system_prompt, user_prompt))
    ctx.write_text("decision_register.md", to_markdown(response))
