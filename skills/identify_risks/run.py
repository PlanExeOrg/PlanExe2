from planexe_skill.planexe import raw_document, structured

RISK_KEYS = ("risk_area", "risk_description", "potential_impact", "likelihood", "severity", "action")


def normalize(r: dict) -> dict:
    return {
        "risks": [{k: str(item.get(k) or "") for k in RISK_KEYS} for item in (r.get("risks") or [])],
        "risk_assessment_summary": str(r.get("risk_assessment_summary") or ""),
    }


def to_markdown(d: dict) -> str:
    rows = []
    if d["risks"]:
        for risk_index, risk in enumerate(d["risks"], start=1):
            rows.append(f"\n## Risk {risk_index} - {risk['risk_area']}")
            rows.append(risk["risk_description"])
            rows.append(f"\n**Impact:** {risk['potential_impact']}")
            rows.append(f"\n**Likelihood:** {risk['likelihood'].capitalize()}")
            rows.append(f"\n**Severity:** {risk['severity'].capitalize()}")
            rows.append(f"\n**Action:** {risk['action']}")
    else:
        rows.append("No risks identified.")

    rows.append(f"\n## Risk summary\n{d['risk_assessment_summary']}")
    return "\n".join(rows)


def run(ctx):
    query = (
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'purpose.md':\n{ctx.read_text('identify_purpose.md')}\n\n"
        f"File 'plan_type.md':\n{ctx.read_text('plan_type.md')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'physical_locations.md':\n{ctx.read_text('physical_locations.md')}\n\n"
        f"File 'currency_strategy.md':\n{ctx.read_text('currency_strategy.md')}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    response = normalize(response)
    ctx.write_json("identify_risks_raw.json", raw_document(response, result, system_prompt, query))
    ctx.write_text("identify_risks.md", to_markdown(response))
