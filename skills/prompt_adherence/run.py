import json

from planexe_skill.planexe import planexe_metadata, structured

DIRECTIVE_TYPE_LABELS = {
    "constraint": "Constraint",
    "stated_fact": "Stated fact",
    "requirement": "Requirement",
    "banned": "Banned",
    "intent": "Intent",
}

CATEGORY_LABELS = {
    "fully_honored": "Fully honored",
    "partially_honored": "Partially honored",
    "softened": "Softened",
    "ignored": "Ignored",
    "contradicted": "Contradicted",
    "unsolicited_caveat": "Unsolicited caveat",
}


def _int(v, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def normalize_directives(response: dict) -> dict:
    out = []
    for i, d in enumerate(response.get("directives") or [], start=1):
        if isinstance(d, dict):
            out.append({"directive_index": _int(d.get("directive_index"), i),
                        "directive_type": str(d.get("directive_type") or ""),
                        "text": str(d.get("text") or ""),
                        "importance_5": _int(d.get("importance_5"), 3)})
    return {"directives": out}


def normalize_scores(response: dict) -> dict:
    out = []
    for i, r in enumerate(response.get("results") or [], start=1):
        if isinstance(r, dict):
            out.append({"directive_index": _int(r.get("directive_index"), i),
                        "adherence_5": _int(r.get("adherence_5"), 1),
                        "category": str(r.get("category") or ""),
                        "evidence": str(r.get("evidence") or ""),
                        "explanation": str(r.get("explanation") or "")})
    return {"results": out}


def format_category(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def escape_table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def to_markdown(directives: dict, scores: dict) -> str:
    lines: list[str] = []
    importance_map = {d["directive_index"]: d for d in directives["directives"]}
    results = scores["results"]

    def importance_of(r) -> int:
        d = importance_map.get(r["directive_index"])
        return d["importance_5"] if d else 3

    weighted_parts, importance_parts, importances = [], [], []
    for r in results:
        importance = importance_of(r)
        importances.append(importance)
        weighted_parts.append(f"{importance}×{r['adherence_5']}")
        importance_parts.append(str(importance))
    weighted_sum = sum(r["adherence_5"] * importance_of(r) for r in results)
    importance_sum = sum(importances)
    overall = round(weighted_sum * 100 / (importance_sum * 5)) if importance_sum > 0 else 100
    lines.append(f"**Overall Adherence: {overall}%**")
    lines.append("")
    if weighted_parts:
        lines.append("```")
        lines.append(f"IMPORTANCE_ADHERENCE_SUM = ({' + '.join(weighted_parts)}) = {weighted_sum}")
        lines.append(f"IMPORTANCE_SUM = {' + '.join(importance_parts)} = {importance_sum}")
        lines.append(f"OVERALL_ADHERENCE = IMPORTANCE_ADHERENCE_SUM / (IMPORTANCE_SUM × 5) = "
                     f"{weighted_sum} / {importance_sum * 5} = {overall}%")
        lines.append("```")
        lines.append("")

    scored_items = []
    for r in results:
        d = importance_map.get(r["directive_index"])
        severity = importance_of(r) * (6 - r["adherence_5"])
        scored_items.append((severity, d, r))
    scored_items.sort(key=lambda x: x[2]["directive_index"])

    lines.append("## Summary")
    lines.append("")
    lines.append("| ID | Directive | Type | Importance | Adherence | Category |")
    lines.append("|----|-----------|------|------------|-----------|----------|")
    for _, d, r in scored_items:
        directive_text = d["text"] if d else "Unknown"
        directive_type = DIRECTIVE_TYPE_LABELS.get(d["directive_type"], d["directive_type"]) if d else "Unknown"
        lines.append(
            f"| {r['directive_index']} | {escape_table_cell(directive_text)} "
            f"| {directive_type} | {d['importance_5'] if d else '?'}/5 "
            f"| {r['adherence_5']}/5 | {format_category(r['category'])} |"
        )
    lines.append("")

    poor_items = [(sev, d, r) for sev, d, r in scored_items if r["adherence_5"] < 5]
    poor_items.sort(key=lambda x: x[0], reverse=True)
    if poor_items:
        lines.append("## Issues")
        lines.append("")
        for _, d, r in poor_items:
            directive_text = d["text"] if d else "Unknown"
            lines.append(f"### Issue {r['directive_index']} - {directive_text}")
            lines.append("")
            lines.append(f"- **Category:** {format_category(r['category'])}")
            lines.append(f"- **Adherence:** {r['adherence_5']}/5")
            lines.append(f"- **Importance:** {d['importance_5'] if d else '?'}/5")
            lines.append(f"- **Evidence:** {r['evidence']}")
            lines.append(f"- **Explanation:** {r['explanation']}")
            lines.append("")
    return "\n".join(lines)


def metadata_of(result) -> dict:
    m = planexe_metadata(result)
    m.pop("duration", None)
    m.pop("response_byte_count", None)
    return m


def run(ctx):
    plan_prompt = ctx.read_json("plan_raw.json")["plan_prompt"]
    plan_context = (
        f"File 'executive_summary.md':\n{ctx.read_text('executive_summary.md')}\n\n"
        f"File 'project_plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"File 'consolidate_assumptions_full.md':\n{ctx.read_text('consolidate_assumptions_full.md')}"
    )
    system_prompt_phase1 = ctx.skill_file("prompts/extract_directives.md").strip()
    system_prompt_phase2 = ctx.skill_file("prompts/score_adherence.md").strip()

    raw1, result1 = structured(ctx, system_prompt_phase1, f"User's original prompt:\n{plan_prompt}",
                               ctx.skill_json("schema_directives.json"), label="phase 1: directives")
    directives = normalize_directives(raw1)

    directives_json = json.dumps(directives, indent=2)
    user_prompt_phase2 = (
        f"User's original prompt:\n{plan_prompt}\n\n"
        f"Extracted directives:\n{directives_json}\n\n"
        f"Final plan artifacts:\n{plan_context}"
    )
    raw2, result2 = structured(ctx, system_prompt_phase2, user_prompt_phase2,
                               ctx.skill_json("schema_scores.json"), label="phase 2: scoring")
    scores = normalize_scores(raw2)

    markdown = to_markdown(directives, scores)
    raw = {
        "directives": directives,
        "scores": scores,
        "metadata": {"phase1": metadata_of(result1), "phase2": metadata_of(result2)},
        "system_prompt_phase1": system_prompt_phase1,
        "system_prompt_phase2": system_prompt_phase2,
        "user_prompt": plan_prompt,
        "markdown": markdown,
    }
    ctx.write_json("prompt_adherence_raw.json", raw)
    ctx.write_text("prompt_adherence.md", markdown)
