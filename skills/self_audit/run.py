import json

from planexe_skill.planexe import planexe_metadata, structured
from planexe_skill.shared.final_review import (PREMORTEM, QUESTIONS_AND_ANSWERS, REVIEW_PLAN,
                                               build_query)

VIOLATES_KNOWN_PHYSICS_INDEX = 1
VIOLATES_KNOWN_PHYSICS_TITLE = "Violates Known Physics"
VIOLATES_KNOWN_PHYSICS_SUBTITLE = (
    "Does the plan's success require breaking a known law of physics "
    "(e.g., thermodynamics, conservation of energy, speed-of-light "
    "limit, causality)?"
)
LEVEL_MAP = {"high": "🛑 High", "medium": "⚠️ Medium", "low": "✅ Low"}
EXPLANATION_MAP = {
    "high": "Existential blocker without credible mitigation.",
    "medium": "Material risk with plausible path.",
    "low": "Minor/controlled risk.",
}


def format_system_prompt(template: str, checklist: list[dict], current_index: int) -> str:
    """PlanExe's format_system_prompt: only the current item keeps its long instruction (status
    TODO); the others are reduced to 'title\\nsubtitle' (status IGNORE)."""
    enriched = [{k: v for k, v in item.items() if k != "comment"} for item in checklist]
    expected_index_to_be_answered = enriched[current_index]["index"]
    instruction_to_follow = enriched[current_index]["instruction"]
    for index, item in enumerate(enriched):
        item["status"] = "TODO" if index == current_index else "IGNORE"
        if index != current_index:
            item["instruction"] = item["title"] + "\n" + item["subtitle"]
    enriched = [{k: v for k, v in item.items() if k not in ("title", "subtitle")} for item in enriched]
    skeleton = json.dumps({"justification": "JUSTIFICATION_PLACEHOLDER",
                           "mitigation": "MITIGATION_PLACEHOLDER",
                           "level": "LEVEL_PLACEHOLDER"}, indent=2)
    return (template
            .replace("{expected_index_to_be_answered}", str(expected_index_to_be_answered))
            .replace("{instruction_to_follow}", instruction_to_follow)
            .replace("{json_enriched_checklist}", json.dumps(enriched, indent=2))
            .replace("{json_response_skeleton}", skeleton))


def answer(response: dict) -> dict:
    return {k: str(response.get(k) or "") for k in ("justification", "mitigation", "level")}


def to_markdown(items: list[dict]) -> str:
    num_low = sum(1 for item in items if item["level"] == "low")
    num_medium = sum(1 for item in items if item["level"] == "medium")
    num_high = sum(1 for item in items if item["level"] == "high")
    rows = ["Reality check: fix before go.\n", "### Summary\n",
            "| Level | Count | Explanation |", "|---|---|---|",
            f"| {LEVEL_MAP['high']} | {num_high} | {EXPLANATION_MAP['high']} |",
            f"| {LEVEL_MAP['medium']} | {num_medium} | {EXPLANATION_MAP['medium']} |",
            f"| {LEVEL_MAP['low']} | {num_low} | {EXPLANATION_MAP['low']} |",
            "\n\n## Checklist\n"]
    for index, item in enumerate(items):
        if index > 0:
            rows.append("\n")
        rows.append(f"## {index + 1}. {item['title']}\n")
        rows.append(f"*{item['subtitle']}*\n")
        rows.append(f"**Level**: {LEVEL_MAP.get(item['level'], 'Unknown level')}\n")
        rows.append(f"**Justification**: {item['justification']}\n")
        rows.append(f"**Mitigation**: {item['mitigation']}")
    return "\n".join(rows)


def run(ctx):
    user_prompt = build_query(ctx, [REVIEW_PLAN, QUESTIONS_AND_ANSWERS, PREMORTEM])
    physics_input = ctx.read_text("plan.txt")
    checklist = ctx.skill_json("checklist.json")
    template = ctx.skill_file("prompts/checklist_system.md")
    schema = ctx.skill_json("schema_checklist_answer.json")

    responses: dict[int, dict] = {}
    metadata_list: list[dict] = []
    user_prompt_list: list[str] = []
    system_prompt_list: list[str] = []
    cleaned: list[dict] = []

    # Item 1: the dedicated physics check on the bare plan prompt.
    physics_system = ctx.skill_file("prompts/violates_known_physics.md").strip()
    raw, result = structured(ctx, physics_system, physics_input, ctx.skill_json("schema_physics.json"),
                             label="1 Violates Known Physics")
    if not raw:
        raise ValueError("LLM returned empty structured response for the physics check.")
    physics = answer(raw)
    physics = {"justification": physics["justification"].strip(), "mitigation": physics["mitigation"].strip(),
               "level": physics["level"].lower().strip()}
    meta = planexe_metadata(result)
    meta.pop("response_byte_count", None)
    system_prompt_list.append(physics_system)
    user_prompt_list.append(physics_input)
    metadata_list.append(meta)
    cleaned.append({"index": VIOLATES_KNOWN_PHYSICS_INDEX, "title": VIOLATES_KNOWN_PHYSICS_TITLE,
                    "subtitle": VIOLATES_KNOWN_PHYSICS_SUBTITLE, **physics})
    responses[VIOLATES_KNOWN_PHYSICS_INDEX] = physics

    # Items 2..20: sequential, each user prompt carries all previous answers (as in PlanExe).
    for index, item in enumerate(checklist):
        system_prompt = format_system_prompt(template, checklist, index)
        system_prompt_list.append(system_prompt)
        previous = json.dumps({str(k): v for k, v in responses.items()}, indent=2)
        prompt = f"{user_prompt}\n\n# Checklist Answers\n{previous}"
        user_prompt_list.append(prompt)
        raw, result = structured(ctx, system_prompt, prompt, schema, label=f"{item['index']} {item['title']}")
        checklist_answer = answer(raw)
        cleaned.append({"index": item["index"], "title": item["title"], "subtitle": item["subtitle"],
                        "justification": checklist_answer["justification"],
                        "mitigation": checklist_answer["mitigation"],
                        "level": checklist_answer["level"].lower()})
        responses[item["index"]] = checklist_answer
        meta = planexe_metadata(result)
        meta.pop("duration", None)
        meta.pop("response_byte_count", None)
        metadata_list.append(meta)

    cleaned.sort(key=lambda x: x["index"])
    raw_doc = {
        "responses": {str(k): v for k, v in responses.items()},
        "metadata": {f"metadata_{i}": m for i, m in enumerate(metadata_list, start=1)},
        "system_prompt_list": system_prompt_list,
        "user_prompt_list": user_prompt_list,
        "checklist_answers_cleaned": cleaned,
    }
    ctx.write_json("self_audit_raw.json", raw_doc)
    ctx.write_text("self_audit.md", to_markdown(cleaned))
