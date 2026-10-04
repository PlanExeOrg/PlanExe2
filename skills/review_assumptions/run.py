from planexe_skill.planexe import raw_document, structured

DOCUMENTS = [
    ("Purpose", "identify_purpose.md"),
    ("Plan Type", "plan_type.md"),
    ("Strategic Decisions", "strategic_decisions.md"),
    ("Scenarios", "scenarios.md"),
    ("Physical Locations", "physical_locations.md"),
    ("Currency Strategy", "currency_strategy.md"),
    ("Identify Risks", "identify_risks.md"),
    ("Make Assumptions", "make_assumptions.md"),
    ("Distill Assumptions", "distill_assumptions.md"),
]
ISSUE_KEYS = ("issue", "explanation", "recommendation", "sensitivity")


def normalize(r: dict) -> dict:
    return {
        "expert_domain": str(r.get("expert_domain") or ""),
        "domain_specific_considerations": [str(x) for x in (r.get("domain_specific_considerations") or [])],
        "issues": [{k: str(i.get(k) or "") for k in ISSUE_KEYS} for i in (r.get("issues") or [])],
        "conclusion": str(r.get("conclusion") or ""),
    }


def to_markdown(d: dict) -> str:
    rows = [f"## Domain of the expert reviewer\n{d['expert_domain']}"]
    if d["domain_specific_considerations"]:
        rows.append("\n## Domain-specific considerations\n")
        for item in d["domain_specific_considerations"]:
            rows.append(f"- {item}")
    else:
        rows.append("\n## Domain-specific considerations - None\n")

    if d["issues"]:
        for index, item in enumerate(d["issues"], start=1):
            rows.append(f"\n## Issue {index} - {item['issue']}")
            rows.append(item["explanation"])
            rows.append(f"\n**Recommendation:** {item['recommendation']}")
            rows.append(f"\n**Sensitivity:** {item['sensitivity']}")
    else:
        rows.append("## Issues - None. This is unusual. Please report this to the developer of PlanExe.")

    rows.append(f"\n## Review conclusion\n{d['conclusion']}")
    return "\n".join(rows)


def run(ctx):
    chunks = []
    for title, name in DOCUMENTS:
        try:
            chunks.append(f"# {title}\n\n{ctx.read_text(name)}")
        except FileNotFoundError:
            ctx.log(f"Markdown file not found: {name} (from {title})")
            chunks.append(f"**Problem with document:** '{title}'\n\nFile not found.")
    full_markdown = "\n\n".join(chunks)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, full_markdown, ctx.skill_json("schema.json"))
    response = normalize(response)
    ctx.write_json("review_assumptions_raw.json", raw_document(response, result, system_prompt, full_markdown))
    ctx.write_text("review_assumptions.md", to_markdown(response))
