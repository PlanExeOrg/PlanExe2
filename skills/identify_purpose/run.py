from planexe_skill.planexe import raw_document, structured


def to_markdown(r: dict) -> str:
    if r["purpose"] == "personal":
        rows = ["**Purpose:** personal"]
    elif r["purpose"] == "business":
        rows = ["**Purpose:** business"]
    elif r["purpose"] == "public_good":
        rows = ["**Purpose:** public_good. This plan is meant to create public value, not profit; judge it by public "
                "value delivered and funding accountability, not by revenue or return on investment."]
    elif r["purpose"] == "other":
        rows = ["**Purpose:** other. This plan doesn't clearly fit into personal, business or public_good categories."]
    else:
        rows = [f"Invalid plan purpose. {r['purpose']}"]
    rows.append(f"\n**Purpose Detailed:** {r['purpose_detailed']}")
    rows.append(f"\n**Topic:** {r['topic']}")
    return "\n".join(rows)


def run(ctx):
    plan = ctx.read_text("plan.txt")
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, plan, ctx.skill_json("schema.json"))
    ctx.write_json("identify_purpose_raw.json", raw_document(response, result, system_prompt, plan))
    ctx.write_text("identify_purpose.md", to_markdown(response))
