import json
import math
import time

from planexe_skill.planexe import planexe_metadata, structured
from planexe_skill.shared.final_review import build_query, transcript


def to_markdown(question_answers_list: list[dict]) -> str:
    rows = []
    for question_index, question_answers in enumerate(question_answers_list, start=1):
        if question_index > 1:
            rows.append("\n")
        title = question_answers.get('title')
        answers = question_answers.get('answers')
        if title is None or answers is None:
            continue
        rows.append(f"## Review {question_index}: {title}\n")
        for answer_index, answer in enumerate(answers, start=1):
            if answer_index > 1:
                rows.append("\n")
            rows.append(f"{answer_index}. {answer}")
    return "\n".join(rows)


def run(ctx):
    document = build_query(ctx)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    system_prompt += "\n\nDocument for review:\n"
    system_prompt += document
    schema = ctx.skill_json("schema.json")
    questions = ctx.skill_json("questions.json")

    # PlanExe runs one growing chat: [system, user q1, assistant a1, user q2, ...]. The calls are
    # sequential because every answer is part of the context for the next question.
    reminder = ctx.skill_file("prompts/question_reminder.md").strip()
    history: list[tuple[str, str]] = []
    question_answers_list, metadata_list, durations, byte_counts = [], [], [], []
    for index, item in enumerate(questions, start=1):
        title, question = item["title"], item["question"]
        user_prompt = transcript(history, f"{question}\n\n{reminder}")
        start = time.perf_counter()
        try:
            try:
                response, result = structured(ctx, system_prompt, user_prompt, schema, label=f"Q{index} {title}")
            except Exception as e:  # PlanExe's LLMExecutor retries a failed interaction
                ctx.log(f"Question {index} failed ({e}); retrying once.")
                response, result = structured(ctx, system_prompt, user_prompt, schema, label=f"Q{index} retry")
            answers = [str(x) for x in response.get("bullet_points") or []]
            if len(answers) != 3:  # the system prompt demands exactly three; ask once more
                ctx.log(f"Question {index} returned {len(answers)} bullet points; retrying once.")
                try:
                    response2, result2 = structured(ctx, system_prompt, user_prompt, schema,
                                                    label=f"Q{index} retry (count)")
                    answers2 = [str(x) for x in response2.get("bullet_points") or []]
                    if len(answers2) == 3:
                        answers, result = answers2, result2
                except Exception as e:
                    ctx.log(f"Question {index} count retry failed ({e}); keeping the first answer.")
        except Exception as e:  # PlanExe uses an empty answer and keeps the conversation going
            ctx.log(f"Question {index} of {len(questions)} failed, using empty answer: {e}")
            question_answers_list.append({"title": title, "question": question, "answers": []})
            metadata_list.append({})
            durations.append(0)
            byte_counts.append(0)
            history += [("User", question), ("Assistant", '{"bullet_points": []}')]
            continue
        content = json.dumps({"bullet_points": answers}, ensure_ascii=False)
        durations.append(int(math.ceil(time.perf_counter() - start)))
        byte_counts.append(len((result.text or content).encode("utf-8")))
        meta = planexe_metadata(result)
        meta.pop("duration", None)
        meta.pop("response_byte_count", None)
        metadata_list.append(meta)
        question_answers_list.append({"title": title, "question": question, "answers": answers})
        history += [("User", question), ("Assistant", content)]

    n = len(questions)
    metadata = {
        "duration_total": sum(durations),
        "duration_average": sum(durations) / n,
        "duration_max": max(durations),
        "duration_min": min(durations),
        "response_byte_count_total": sum(byte_counts),
        "response_byte_count_average": sum(byte_counts) / n,
        "response_byte_count_max": max(byte_counts),
        "response_byte_count_min": min(byte_counts),
        "metadata_list": metadata_list,
    }
    raw = {"question_answers_list": question_answers_list, "metadata": metadata, "system_prompt": system_prompt}
    ctx.write_json("review_plan_raw.json", raw)
    ctx.write_text("review_plan.md", to_markdown(question_answers_list))
