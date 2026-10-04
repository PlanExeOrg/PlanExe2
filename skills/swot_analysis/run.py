from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured

LIST_KEYS = ["strengths", "weaknesses", "opportunities", "threats", "recommendations", "strategic_objectives",
             "assumptions", "missing_information", "user_questions"]

SECTIONS = [
    ("Strengths 👍💪🦾", "strengths"),
    ("Weaknesses 👎😱🪫⚠️", "weaknesses"),
    ("Opportunities 🌈🌐", "opportunities"),
    ("Threats ☠️🛑🚨☢︎💩☣︎", "threats"),
    ("Recommendations 💡✅", "recommendations"),
    ("Strategic Objectives 🎯🔭⛳🏅", "strategic_objectives"),
    ("Assumptions 🤔🧠🔍", "assumptions"),
    ("Missing Information 🧩🤷‍♂️🤷‍♀️", "missing_information"),
    ("Questions 🙋❓💬📌", "user_questions"),
]


def select_system_prompt(ctx, purpose_info: dict) -> str:
    purpose = purpose_info.get("purpose")
    if purpose == "business":
        system_prompt = ctx.skill_file("prompts/business.md")
    elif purpose == "personal":
        system_prompt = ctx.skill_file("prompts/personal.md")
    elif purpose == "other":
        system_prompt = ctx.skill_file("prompts/other.md")
        system_prompt = system_prompt.replace("INSERT_USER_TOPIC_HERE", purpose_info["topic"])
        system_prompt = system_prompt.replace("INSERT_USER_SWOTTYPEDETAILED_HERE", purpose_info["purpose_detailed"])
    else:
        raise ValueError(f"Invalid purpose: {purpose}, must be one of 'business', 'personal', or 'other'. "
                         f"Cannot perform SWOT analysis.")
    return system_prompt.strip()


def to_markdown(conduct: dict) -> str:
    rows = []
    for heading, key in SECTIONS:
        rows.append(f"\n## {heading}")
        for item in conduct.get(key, []):
            rows.append(f"- {item}")
    return "\n".join(rows)


def run(ctx):
    query = (
        f"File 'initial-plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'assumptions.md':\n{ctx.read_text('consolidate_assumptions_short.md')}\n\n"
        f"File 'pre-project-assessment.json':\n{format_json_for_query(ctx.read_json('pre_project_assessment.json'))}\n\n"
        f"File 'project-plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"File 'related-resources.md':\n{ctx.read_text('related_resources.md')}"
    )
    identify_purpose_dict = ctx.read_json("identify_purpose_raw.json")
    system_prompt = select_system_prompt(ctx, identify_purpose_dict)

    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    conduct = {k: [str(x) for x in (response.get(k) or [])] for k in LIST_KEYS}
    conduct["metadata"] = planexe_metadata(result)

    metadata = planexe_metadata(result)
    metadata.pop("response_byte_count", None)
    metadata["query"] = query
    raw = {
        "query": query,
        "topic": identify_purpose_dict["topic"],
        "purpose": identify_purpose_dict["purpose"],
        "purpose_detailed": identify_purpose_dict["purpose_detailed"],
        "response_purpose": identify_purpose_dict,
        "response_conduct": conduct,
        "metadata": metadata,
    }
    ctx.write_json("swot_analysis_raw.json", raw)
    ctx.write_text("swot_analysis.md", to_markdown(conduct))
