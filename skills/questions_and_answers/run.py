import json
import math
import time

from planexe_skill.planexe import planexe_metadata, structured
from planexe_skill.shared.final_review import REVIEW_PLAN, build_query, transcript


def normalize(response: dict) -> dict:
    """Mirror pydantic's model_dump (every field present, in schema order)."""
    pairs = []
    for i, p in enumerate(response.get("question_answer_pairs") or [], start=1):
        if not isinstance(p, dict):
            continue
        try:
            item_index = int(p.get("item_index"))
        except (TypeError, ValueError):
            item_index = i
        pairs.append({"item_index": item_index, "question": str(p.get("question") or ""),
                      "answer": str(p.get("answer") or ""), "rationale": str(p.get("rationale") or "")})
    return {"question_answer_pairs": pairs, "summary": str(response.get("summary") or "")}


def to_markdown(pairs: list[dict]) -> str:
    rows = []
    for index, item in enumerate(pairs, start=1):
        rows.append(f"**Q{index}: {item['question']}**")
        rows.append(f"A{index}: {item['answer']}")
    return "\n\n".join(rows)


def run(ctx):
    user_prompt = build_query(ctx, [REVIEW_PLAN])
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    second_user_prompt = ctx.skill_file("prompts/second_user.md").strip()
    schema = ctx.skill_json("schema.json")

    start = time.perf_counter()
    raw1, result1 = structured(ctx, system_prompt, user_prompt, schema, label="call 1")
    duration1 = int(math.ceil(time.perf_counter() - start))
    response1 = normalize(raw1)

    # PlanExe's follow-up: [system, user, assistant(response 1), user(SECOND_USER_PROMPT)].
    followup = transcript([("Assistant", json.dumps(response1))], second_user_prompt, initial=user_prompt)
    start = time.perf_counter()
    raw2, result2 = structured(ctx, system_prompt, followup, schema, label="call 2")
    duration2 = int(math.ceil(time.perf_counter() - start))
    response2 = normalize(raw2)

    pairs1 = response1["question_answer_pairs"]
    pairs2 = response2["question_answer_pairs"]
    for qa in pairs2:
        qa["item_index"] = len(pairs1) + qa["item_index"]
    summary1, summary2 = response1["summary"], response2["summary"]
    combined_summary = f"{summary1}\n\n{summary2}" if summary1 and summary2 else summary1 or summary2
    merged = {"question_answer_pairs": pairs1 + pairs2, "summary": combined_summary}

    metadata = planexe_metadata(result1)
    metadata.pop("duration", None)
    metadata.pop("response_byte_count", None)
    metadata["duration1"] = duration1
    metadata["duration2"] = duration2
    metadata["response_byte_count1"] = planexe_metadata(result1)["response_byte_count"]
    metadata["response_byte_count2"] = planexe_metadata(result2)["response_byte_count"]

    raw = dict(merged)
    raw["metadata"] = metadata
    raw["system_prompt"] = system_prompt
    raw["user_prompt"] = user_prompt
    ctx.write_json("questions_and_answers_raw.json", raw)
    ctx.write_text("questions_and_answers.md", to_markdown(merged["question_answer_pairs"]))
