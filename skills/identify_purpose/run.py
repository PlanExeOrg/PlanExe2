from planexe_skill.planexe import raw_document, structured


def to_markdown(r: dict) -> str:
    if r["purpose"] == "personal":
        rows = ["**Purpose:** personal"]
    elif r["purpose"] == "business" and r.get("profit_motive") == "non_profit":
        rows = ["**Purpose:** business, non-profit. This plan is not run for profit; judge it by the value it delivers "
                "to its members, beneficiaries or the public and by funding accountability, not by revenue or return "
                "on investment."]
    elif r["purpose"] == "business" and r.get("profit_motive") == "other":
        rows = ["**Purpose:** business, neither for profit nor non-profit (e.g., a government programme, an agreement "
                "between countries, a public-private hybrid). No owner profits from it; judge it by its outcomes for "
                "the parties involved and by funding accountability, and use revenue or return on investment only for "
                "parts of the plan that earn money."]
    elif r["purpose"] == "business":
        rows = ["**Purpose:** business"]
    elif r["purpose"] == "other":
        rows = ["**Purpose:** other. This plan doesn't clearly fit into personal or business categories."]
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
