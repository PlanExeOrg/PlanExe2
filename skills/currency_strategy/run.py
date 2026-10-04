from planexe_skill.planexe import raw_document, structured


def normalize(r: dict) -> dict:
    """Mirror pydantic's model_dump: optional fields present with their defaults."""
    return {
        "money_involved": bool(r.get("money_involved")),
        "currency_list": [{"currency": str(c.get("currency") or ""), "consideration": str(c.get("consideration") or "")}
                          for c in (r.get("currency_list") or [])],
        "primary_currency": r.get("primary_currency"),
        "currency_strategy": str(r.get("currency_strategy") or ""),
    }


def to_markdown(d: dict) -> str:
    rows = []
    if d["money_involved"]:
        rows.append("This plan involves money.")
    else:
        rows.append("This plan **does not** involve money.")

    if d["currency_list"]:
        rows.append("\n## Currencies\n")
        for item in d["currency_list"]:
            rows.append(f"- **{item['currency']}:** {item['consideration']}")
    else:
        rows.append("No currencies identified.")

    rows.append(f"\n**Primary currency:** {d['primary_currency']}")
    rows.append(f"\n**Currency strategy:** {d['currency_strategy']}")
    return "\n".join(rows)


def run(ctx):
    query = (
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'purpose.md':\n{ctx.read_text('identify_purpose.md')}\n\n"
        f"File 'plan_type.md':\n{ctx.read_text('plan_type.md')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'physical_locations.md':\n{ctx.read_text('physical_locations.md')}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    response = normalize(response)
    ctx.write_json("currency_strategy_raw.json", raw_document(response, result, system_prompt, query))
    ctx.write_text("currency_strategy.md", to_markdown(response))
