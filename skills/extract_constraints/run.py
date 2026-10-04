from planexe_skill.planexe import raw_document, structured


def to_markdown(r: dict) -> str:
    constraints = r.get("constraints") or []
    if not constraints:
        return "No constraints identified."
    parts = []
    for label, kind in (("Positive", "positive"), ("Negative", "negative")):
        items = [c for c in constraints if c["classification"] == kind]
        if items:
            parts.append(f"## {label} Constraints\n")
            parts.extend(f"- {c['constraint_text']}" for c in items)
            parts.append("")
    return "\n".join(parts)


def run(ctx):
    plan = ctx.read_text("plan.txt")
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, plan, ctx.skill_json("schema.json"))
    ctx.write_json("extract_constraints_raw.json", raw_document(response, result, system_prompt, plan))
    ctx.write_text("extract_constraints.md", to_markdown(response))
