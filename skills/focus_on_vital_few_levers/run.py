import json
import math

from planexe_skill.planexe import planexe_metadata, structured

TARGET_VITAL_LEVER_COUNT = 5
LEVER_KEYS = ("lever_id", "name", "consequences", "options", "review", "description", "synergy_text",
              "conflict_text")
IMPORTANCE_ORDER = ("Critical", "High", "Medium", "Low")


def focus_prompt(project_context: str, levers: list[dict]) -> str:
    return (
        f"**Project Context:**\n{project_context}\n\n"
        f"**Candidate Levers List:**\n"
        f"Please assess the strategic importance of the following "
        f"{len(levers)} levers based on the project plan and "
        f"their detailed characterizations:\n\n"
        f"{json.dumps(levers, indent=2)}"
    )


def normalize(response: dict) -> dict:
    assessments = [{
        "lever_id": str(a.get("lever_id", "")),
        "lever_name": str(a.get("lever_name", "")),
        "strategic_importance": a.get("strategic_importance"),
        "justification": str(a.get("justification", "")),
    } for a in response.get("lever_assessments") or []]
    return {"lever_assessments": assessments, "summary": str(response.get("summary", ""))}


def metadata_of(result) -> dict:
    meta = planexe_metadata(result)
    meta.pop("duration", None)
    meta.pop("response_byte_count", None)
    return meta


def compute_batch_size(total: int, max_batch: int = 4) -> int:
    if total <= max_batch:
        return total
    num_batches = math.ceil(total / max_batch)
    return math.ceil(total / num_batches)


def make_batches(items: list, batch_size: int) -> list[list]:
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    if len(batches) >= 2 and len(batches[-1]) == 1:
        batches[-2].extend(batches.pop())
    return batches


def assess_batched(ctx, system_prompt, schema, project_context, levers):
    """PlanExe's fallback: compressed levers (id, name, description, synergy, conflict) in even batches."""
    compressed = [{k: lv[k] for k in ("lever_id", "name", "description", "synergy_text", "conflict_text")}
                  for lv in levers]
    batches = make_batches(compressed, compute_batch_size(len(compressed)))
    assessments, summaries, metas, last_prompt = [], [], [], ""
    for n, batch in enumerate(batches, start=1):
        prompt = focus_prompt(project_context, batch)
        last_prompt = prompt
        try:
            response, result = structured(ctx, system_prompt, prompt, schema, label=f"batch {n}")
        except Exception as e:
            ctx.log(f"Batch {n} failed: {e}")
            continue
        response = normalize(response)
        assessments.extend(response["lever_assessments"])
        summaries.append(response["summary"])
        meta = metadata_of(result)
        meta["lever_count"] = len(batch)
        metas.append(meta)
    if not assessments:
        raise ValueError("All batched lever assessments failed. No levers could be assessed.")
    combined = {"batched": True, "batch_count": len(metas)}
    for i, m in enumerate(metas, start=1):
        combined[f"batch_{i}"] = m
    return {"lever_assessments": assessments, "summary": "\n\n".join(summaries)}, combined, last_prompt


def select_top_levers(levers: list[dict], assessment: dict, target_count: int) -> list[dict]:
    by_importance: dict[str, list[str]] = {k: [] for k in IMPORTANCE_ORDER}
    for a in assessment["lever_assessments"]:
        if a["strategic_importance"] in by_importance:
            by_importance[a["strategic_importance"]].append(a["lever_id"])
    selected: list[str] = []
    for level in IMPORTANCE_ORDER:
        if len(selected) >= target_count:
            break
        for lever_id in by_importance[level]:
            if len(selected) < target_count:
                selected.append(lever_id)
            else:
                break
    return [lv for lv in levers if lv["lever_id"] in selected]


def run(ctx):
    plan_prompt = ctx.read_text("plan.txt")
    identify_purpose_markdown = ctx.read_text("identify_purpose.md")
    plan_type_markdown = ctx.read_text("plan_type.md")
    raw_levers = ctx.read_json("enriched_levers_raw.json")["characterized_levers"]
    if not raw_levers:
        raise ValueError("No valid enriched levers were provided.")
    project_context = (
        f"File 'plan.txt':\n{plan_prompt}\n\n"
        f"File 'purpose.md':\n{identify_purpose_markdown}\n\n"
        f"File 'plan_type.md':\n{plan_type_markdown}\n\n"
    )
    # EnrichedLever(**lever).model_dump(): classification/deduplication_justification are dropped.
    levers = [{k: lever[k] for k in LEVER_KEYS} for lever in raw_levers]
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    schema = ctx.skill_json("schema.json")

    try:
        user_prompt = focus_prompt(project_context, levers)
        response, result = structured(ctx, system_prompt, user_prompt, schema, label="full assessment")
        response = normalize(response)
        metadata = metadata_of(result)
    except Exception as e:
        ctx.log(f"Full lever assessment failed ({type(e).__name__}: {e}). Falling back to batched processing.")
        response, metadata, user_prompt = assess_batched(ctx, system_prompt, schema, project_context, levers)

    vital = select_top_levers(levers, response, TARGET_VITAL_LEVER_COUNT)
    out = {"response": response, "levers": vital, "metadata": metadata,
           "system_prompt": system_prompt, "user_prompt": user_prompt}
    ctx.write_text("vital_few_levers_raw.json", json.dumps(out, indent=2))
