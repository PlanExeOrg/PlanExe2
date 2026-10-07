import json
import re

from planexe_skill.planexe import format_json_for_query, raw_document, structured

SEVERITY_ICON = {"high": "🔴 High", "medium": "🟡 Medium"}


def cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def to_markdown(r: dict) -> str:
    decisions = r.get("decisions") or []
    high = sum(1 for d in decisions if d.get("severity") == "high")
    count = (f"**{len(decisions)} open decision(s): {high} high, {len(decisions) - high} medium severity.**"
             if decisions else "")
    rows = [f"{count} {r.get('summary', '')}".strip(), ""]
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
    uncovered = r.get("uncovered_candidates") or []
    if uncovered:
        rows += ["## Also open", "", "Open items from the consistency check or the canonical facts that no decision above "
                 "covers:", ""] + [f"- {u['id']}: {u['text']}" for u in uncovered] + [""]
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


def candidates(recheck: dict, facts: list[dict]) -> list[tuple[str, str]]:
    """(id, text) for every item the inputs show to be open: needs_decision contradictions (high/medium)
    and canonical facts whose value is OPEN (a value listing several items is split on ';')."""
    out = []
    items = [c for c in recheck.get("contradictions") or []
             if c.get("resolution_type") == "needs_decision" and c.get("severity") in ("high", "medium")]
    for i, c in enumerate(items, start=1):
        out.append((f"C{i}", f"[{c['severity']}] {c.get('topic', '')}: {c.get('suggested_resolution', '')}"))
    n = 0
    for f in facts:
        value = str(f.get("value", ""))
        if not value.strip().upper().startswith("OPEN"):
            continue
        n += 1
        body = re.sub(r"^\s*OPEN\s*[:\-–]?\s*", "", value, flags=re.IGNORECASE)
        parts = [p.strip() for p in body.split(";") if p.strip()] or [body]
        for j, part in enumerate(parts):
            suffix = chr(97 + j) if len(parts) > 1 else ""
            out.append((f"F{n}{suffix}", f"{f.get('key', '')}: {part}"))
    return out


def run(ctx):
    recheck = ctx.read_json("consistency_recheck_raw.json")
    facts = ctx.read_json("canonical_facts.json").get("facts") or []
    cands = candidates(recheck, facts)
    selected = ctx.read_json("selected_scenario.json")
    sections = [
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}",
        f"File 'consistency_recheck_raw.json' (final consistency check):\n{format_json_for_query(recheck)}",
        f"File 'selected_scenario.json' (final choice):\n{json.dumps(selected.get('final_choice', selected), ensure_ascii=False)}",
        f"File 'candidate_scenarios.json':\n{format_json_for_query(ctx.read_json('candidate_scenarios.json'))}",
        f"File 'governance_phase4_decision_escalation_matrix.md':\n{ctx.read_text('governance_phase4_decision_escalation_matrix.md')}",
    ]
    sections.append("# Candidate open items (cover each exactly once)\n"
                    + ("\n".join(f"- {cid}: {text}" for cid, text in cands) or "(none)"))
    user_prompt = "\n\n".join(sections)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    covered = {c for d in response.get("decisions") or [] for c in d.get("covers") or []}
    missing = [cid for cid, _ in cands if cid not in covered]
    if missing:
        ctx.log(f"candidate open items not covered by any decision: {', '.join(missing)}")
    response["uncovered_candidates"] = [{"id": cid, "text": text} for cid, text in cands if cid in missing]
    ctx.write_json("decision_register_raw.json", raw_document(response, result, system_prompt, user_prompt))
    ctx.write_text("decision_register.md", to_markdown(response))
