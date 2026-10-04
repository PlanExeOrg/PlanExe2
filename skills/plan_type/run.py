from planexe_skill.planexe import raw_document, structured


def to_markdown(d: dict) -> str:
    if d["plan_type"] == "digital":
        rows = ["This plan is purely digital and can be automated. There is no need for any physical locations."]
    elif d["plan_type"] == "physical":
        rows = ["This plan requires one or more physical locations. It cannot be executed digitally."]
    else:
        rows = [f"Invalid plan type. {d['plan_type']}"]
    rows.append(f"\n**Explanation:** {d['explanation']}")
    return "\n".join(rows)


def run(ctx):
    query = (f"File 'plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
             f"File 'classify_domain.md':\n{ctx.read_text('classify_domain.md')}\n\n"
             f"File 'purpose.md':\n{ctx.read_text('identify_purpose.md')}")
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    ctx.write_json("plan_type_raw.json", raw_document(response, result, system_prompt, query))
    ctx.write_text("plan_type.md", to_markdown(response))
