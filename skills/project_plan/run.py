from planexe_skill.planexe import format_json_for_query, raw_document, structured

SMART_KEYS = ("specific", "measurable", "achievable", "relevant", "time_bound")
LIST_KEYS = ("dependencies", "resources_required", "related_goals", "tags")
GROUPS = {
    "risk_assessment_and_mitigation_strategies": ("key_risks", "diverse_risks", "mitigation_plans"),
    "stakeholder_analysis": ("primary_stakeholders", "secondary_stakeholders", "engagement_strategies"),
    "regulatory_and_compliance_requirements": ("permits_and_licenses", "compliance_standards",
                                               "regulatory_bodies", "compliance_actions"),
}


def _list(v) -> list:
    return [str(x) for x in (v or [])]


def normalize(r: dict) -> dict:
    """Mirror pydantic's model_dump: every field present, in schema order."""
    smart = r.get("smart_criteria") or {}
    d = {"goal_statement": str(r.get("goal_statement") or ""),
         "smart_criteria": {k: str(smart.get(k) or "") for k in SMART_KEYS}}
    for k in LIST_KEYS:
        d[k] = _list(r.get(k))
    for group, keys in GROUPS.items():
        g = r.get(group) or {}
        d[group] = {k: _list(g.get(k)) for k in keys}
    return d


def to_markdown(d: dict) -> str:
    rows = [f"**Goal Statement:** {d['goal_statement']}"]
    s = d["smart_criteria"]
    rows.append("\n## SMART Criteria\n")
    rows.append(f"- **Specific:** {s['specific']}")
    rows.append(f"- **Measurable:** {s['measurable']}")
    rows.append(f"- **Achievable:** {s['achievable']}")
    rows.append(f"- **Relevant:** {s['relevant']}")
    rows.append(f"- **Time-bound:** {s['time_bound']}")

    def section(heading: str, items: list) -> None:
        rows.append(heading)
        rows.extend(f"- {x}" for x in items)

    section("\n## Dependencies\n", d["dependencies"])
    section("\n## Resources Required\n", d["resources_required"])
    section("\n## Related Goals\n", d["related_goals"])
    section("\n## Tags\n", d["tags"])

    risk = d["risk_assessment_and_mitigation_strategies"]
    rows.append("\n## Risk Assessment and Mitigation Strategies\n")
    section("\n### Key Risks\n", risk["key_risks"])
    section("\n### Diverse Risks\n", risk["diverse_risks"])
    section("\n### Mitigation Plans\n", risk["mitigation_plans"])

    st = d["stakeholder_analysis"]
    rows.append("\n## Stakeholder Analysis\n")
    section("\n### Primary Stakeholders\n", st["primary_stakeholders"])
    section("\n### Secondary Stakeholders\n", st["secondary_stakeholders"])
    section("\n### Engagement Strategies\n", st["engagement_strategies"])

    reg = d["regulatory_and_compliance_requirements"]
    rows.append("\n## Regulatory and Compliance Requirements\n")
    section("\n### Permits and Licenses\n", reg["permits_and_licenses"])
    section("\n### Compliance Standards\n", reg["compliance_standards"])
    section("\n### Regulatory Bodies\n", reg["regulatory_bodies"])
    section("\n### Compliance Actions\n", reg["compliance_actions"])
    return "\n".join(rows)


def run(ctx):
    query = (
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'assumptions.md':\n{ctx.read_text('consolidate_assumptions_short.md')}\n\n"
        f"File 'pre-project-assessment.json':\n{format_json_for_query(ctx.read_json('pre_project_assessment.json'))}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    response = normalize(response)
    raw = dict(response)
    raw["metadata"] = raw_document({}, result, "", "")["metadata"]
    raw["user_prompt"] = query      # PlanExe's ProjectPlan.to_dict puts user_prompt before system_prompt
    raw["system_prompt"] = system_prompt
    ctx.write_json("project_plan_raw.json", raw)
    ctx.write_text("project_plan.md", to_markdown(response))
