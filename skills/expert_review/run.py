import json
import uuid

from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured

MAX_EXPERT_COUNT = 2
EXPERT_KEYS = ["expert_title", "expert_knowledge", "expert_why", "expert_what", "expert_relevant_skills",
               "expert_search_query"]


def call_with_retry(ctx, system_prompt: str, user_prompt: str, schema: dict, label: str):
    """PlanExe runs these calls through LLMExecutor, which retries a failed interaction; mirror that
    with one retry (e.g. the claude CLI's occasional structured_output_retry_exhausted)."""
    try:
        return structured(ctx, system_prompt, user_prompt, schema, label=label)
    except Exception as e:
        ctx.log(f"{label} failed ({e}); retrying once.")
        return structured(ctx, system_prompt, user_prompt, schema, label=f"{label} (retry)")


# ---------- phase 1: ExpertFinder ----------

def normalize_experts(response: dict) -> list[dict]:
    return [{k: str(e.get(k, "")) for k in EXPERT_KEYS}
            for e in response.get("experts") or [] if isinstance(e, dict)]


def find_experts(ctx, query: str):
    system_prompt = ctx.skill_file("prompts/expert_finder.md").strip()
    schema = ctx.skill_json("schema_experts.json")

    response1, result1 = call_with_retry(ctx, system_prompt, query, schema, "experts 1")
    experts1 = normalize_experts(response1)
    # PlanExe continues the chat: [system, user, assistant(response 1), user("4 more please")].
    followup = (
        f"{query}\n\n"
        f"## Conversation so far\n\n"
        f"### Assistant (previous step)\n{json.dumps({'experts': experts1})}\n\n"
        f"### User\n4 more please"
    )
    response2, result2 = call_with_retry(ctx, system_prompt, followup, schema, "experts 2")
    experts2 = normalize_experts(response2)

    def meta(result, experts):
        m = planexe_metadata(result)
        m["expert_count"] = len(experts)
        return m

    merged = {"experts": experts1 + experts2}
    expert_list = [{
        "id": str(uuid.uuid4()),
        "title": e["expert_title"],
        "knowledge": e["expert_knowledge"],
        "why": e["expert_why"],
        "what": e["expert_what"],
        "skills": e["expert_relevant_skills"],
        "search_query": e["expert_search_query"],
    } for e in merged["experts"]]
    raw = dict(merged)
    raw["metadata"] = {"result1": meta(result1, experts1), "result2": meta(result2, experts2)}
    raw["system_prompt"] = system_prompt
    raw["user_prompt"] = query
    return raw, expert_list


# ---------- phase 2: ExpertCriticism ----------

def format_system(template: str, expert: dict) -> str:
    s = template.strip()
    s = s.replace("PLACEHOLDER_ROLE", expert.get("title", "No role specified"))
    s = s.replace("PLACEHOLDER_KNOWLEDGE", expert.get("knowledge", "No knowledge specified"))
    s = s.replace("PLACEHOLDER_SKILLS", expert.get("skills", "No skills specified"))
    return s


def normalize_criticism(response: dict) -> dict:
    feedback = []
    for i, item in enumerate(response.get("negative_feedback_list") or [], start=1):
        if not isinstance(item, dict):
            continue
        tags = item.get("feedback_problem_tags")
        feedback.append({
            "feedback_index": item.get("feedback_index", i),
            "feedback_title": str(item.get("feedback_title", "")),
            "feedback_verbose": str(item.get("feedback_verbose", "")),
            "feedback_problem_tags": [str(t) for t in tags] if isinstance(tags, list) else [],
            "feedback_mitigation": str(item.get("feedback_mitigation", "")),
            "feedback_consequence": str(item.get("feedback_consequence", "")),
            "feedback_root_cause": str(item.get("feedback_root_cause", "") or ""),
        })
    return {
        "negative_feedback_list": feedback,
        "user_primary_actions": [str(x) for x in response.get("user_primary_actions") or []],
        "user_secondary_actions": [str(x) for x in response.get("user_secondary_actions") or []],
        "follow_up_consultation": str(response.get("follow_up_consultation", "") or ""),
    }


# ---------- markdown ----------

def rows_expert_info(section_index: int, e: dict) -> list[str]:
    return [
        f"# {section_index} Expert: {e.get('title', 'Missing title')}",
        f"\n**Knowledge**: {e.get('knowledge', 'Missing knowledge')}",
        f"\n**Why**: {e.get('why', 'Missing why')}",
        f"\n**What**: {e.get('what', 'Missing what')}",
        f"\n**Skills**: {e.get('skills', 'Missing skills')}",
        f"\n**Search**: {e.get('search_query', 'Missing search_query')}",
    ]


def _bullets_or_empty(rows: list[str], items) -> None:
    if isinstance(items, list) and len(items) > 0:
        rows.extend(f"- {x}" for x in items)
    else:
        rows.append("Empty")


def rows_criticism(section_index: int, c: dict) -> list[str]:
    rows = [""]
    rows.append(f"## {section_index}.1 Primary Actions\n")
    _bullets_or_empty(rows, c.get("user_primary_actions"))
    rows.append(f"\n## {section_index}.2 Secondary Actions\n")
    _bullets_or_empty(rows, c.get("user_secondary_actions"))
    rows.append(f"\n## {section_index}.3 Follow Up Consultation\n")
    rows.append(c.get("follow_up_consultation") or "Empty")
    for feedback_index, item in enumerate(c.get("negative_feedback_list", [])):
        rows.append("")
        p = f"{section_index}.{4 + feedback_index}"
        rows.append(f"## {p}.A Issue - {item.get('feedback_title', 'Missing feedback_title')}\n")
        rows.append(item.get("feedback_verbose", "Missing feedback_verbose"))
        rows.append(f"\n### {p}.B Tags\n")
        _bullets_or_empty(rows, item.get("feedback_problem_tags"))
        rows.append(f"\n### {p}.C Mitigation\n")
        rows.append(item.get("feedback_mitigation") or "Empty")
        rows.append(f"\n### {p}.D Consequence\n")
        rows.append(item.get("feedback_consequence") or "Empty")
        rows.append(f"\n### {p}.E Root Cause\n")
        rows.append(item.get("feedback_root_cause") or "Empty")
    return rows


def to_markdown(expert_list: list[dict], criticisms: list[dict]) -> str:
    rows = ["# Project Expert Review & Recommendations\n",
            "## A Compilation of Professional Feedback for Project Planning and Execution\n\n"]
    for i, c in enumerate(criticisms):
        if i > 0:
            rows.append("\n---\n")
        rows.extend(rows_expert_info(i + 1, expert_list[i]))
        rows.extend(rows_criticism(i + 1, c))
    if len(criticisms) != len(expert_list):
        rows.append("\n---\n")
        rows.append("# The following experts did not provide feedback:")
        for i, e in enumerate(expert_list):
            if i < len(criticisms):
                continue
            rows.append("")
            rows.extend(rows_expert_info(i + 1, e))
    return "\n".join(rows)


def run(ctx):
    query = (
        f"File 'initial-plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'pre-project assessment.json':\n{format_json_for_query(ctx.read_json('pre_project_assessment.json'))}\n\n"
        f"File 'project_plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"File 'SWOT Analysis.md':\n{ctx.read_text('swot_analysis.md')}"
    )

    experts_raw, expert_list = find_experts(ctx, query)
    ctx.write_json("experts_raw.json", experts_raw)
    ctx.write_json("experts.json", expert_list)

    template = ctx.skill_file("prompts/expert_criticism.md")
    schema = ctx.skill_json("schema_criticism.json")

    def criticize(item):
        index, expert = item
        system_prompt = format_system(template, expert)
        try:
            response, result = call_with_retry(ctx, system_prompt, query, schema, f"expert {index + 1}")
        except Exception as e:
            raise ValueError(f"Expert {index + 1} criticism LLM interaction failed.") from e
        response = normalize_criticism(response)
        meta = planexe_metadata(result)
        meta.pop("response_byte_count", None)
        raw = dict(response)
        raw["metadata"] = meta
        raw["query"] = query
        ctx.write_json(f"expert_criticism_{index + 1}_raw.json", raw)
        return response

    criticisms = ctx.map(criticize, list(enumerate(expert_list[:MAX_EXPERT_COUNT])))
    ctx.write_text("expert_criticism.md", to_markdown(expert_list, criticisms))
