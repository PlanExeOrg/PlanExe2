import json
import threading
import time

from planexe_skill.planexe import planexe_metadata, structured

BATCH_SIZE = 5
MAX_RETRY_DEPTH = 1
MAX_RETRY_BUDGET_SECONDS = 300
INPUT_KEYS = ("lever_id", "name", "consequences", "options", "review", "classification",
              "deduplication_justification")
ENRICH_KEYS = ("description", "synergy_text", "conflict_text")


def run(ctx):
    plan_prompt = ctx.read_text("plan.txt")
    identify_purpose_markdown = ctx.read_text("identify_purpose.md")
    plan_type_markdown = ctx.read_text("plan_type.md")
    raw_levers = ctx.read_json("triaged_levers_raw.json")["triaged_levers"]
    project_context = (
        f"File 'plan.txt':\n{plan_prompt}\n\n"
        f"File 'purpose.md':\n{identify_purpose_markdown}\n\n"
        f"File 'plan_type.md':\n{plan_type_markdown}"
    )
    # InputLever(**lever).model_dump(): classification is Optional (defaults to None).
    levers = [{k: lever.get(k) for k in INPUT_KEYS} for lever in raw_levers]
    if not levers:
        raise ValueError("The list of levers to characterize cannot be empty.")

    system_prompt = ctx.skill_file("prompts/system.md").strip()
    schema = ctx.skill_json("schema.json")
    full_lever_context_str = "\n".join(f"- {lever['name']}" for lever in levers)
    enriched_map = {lever["lever_id"]: dict(lever) for lever in levers}
    lock = threading.Lock()
    all_metadata: list[dict] = []
    errors: list[dict] = []
    batches_succeeded = 0
    retry_start_time = time.monotonic()

    def process(batch: list[dict], depth: int) -> None:
        """One batch call; on failure split in half and retry once (PlanExe's retry guards)."""
        nonlocal batches_succeeded
        lever_details = "\n\n".join(
            f"<lever>{lever['lever_id']}</lever>\n"
            f"Name: {lever['name']}\n"
            f"Consequences: {lever['consequences']}\n"
            f"Options: {json.dumps(lever['options'])}\n"
            f"Review: {lever['review']}"
            for lever in batch
        )
        user_prompt = (
            f"**Project Context:**\n{project_context}\n\n"
            f"**Full List of All Levers (for context):**\n{full_lever_context_str}\n\n"
            "---\n\n"
            f"**Levers to Characterize in this Batch:**\n"
            f"Please provide the `description`, `synergy_text`, and `conflict_text` for the following {len(batch)} levers. "
            f"Return exactly {len(batch)} characterizations — one per lever, no more, no fewer. "
            f"Analyze them against the full list provided above.\n\n"
            f"{lever_details}"
        )
        try:
            response, result = structured(ctx, system_prompt, user_prompt, schema,
                                          label=f"batch of {len(batch)} (depth={depth})")
            chars = response.get("characterizations")
            if not isinstance(chars, list):
                raise ValueError("response has no 'characterizations' list")
        except Exception as e:
            lever_ids = [lever["lever_id"] for lever in batch]
            elapsed = time.monotonic() - retry_start_time
            error_str = f"{type(e).__name__}: {e}"
            if len(batch) > 1 and depth < MAX_RETRY_DEPTH and elapsed < MAX_RETRY_BUDGET_SECONDS:
                with lock:
                    errors.append({"type": "batch_retry", "lever_ids": lever_ids, "depth": depth, "error": error_str})
                mid = len(batch) // 2
                process(batch[:mid], depth + 1)
                process(batch[mid:], depth + 1)
            else:
                ctx.log(f"Batch failed for {lever_ids}, skipping: {error_str}")
                with lock:
                    errors.append({"type": "batch_skipped", "lever_ids": lever_ids, "depth": depth, "error": error_str})
            return
        meta = planexe_metadata(result)
        meta.pop("duration", None)
        meta.pop("response_byte_count", None)
        with lock:
            all_metadata.append(meta)
            batches_succeeded += 1
            for char in chars:
                lever_id = char.get("lever_id")
                if lever_id in enriched_map:
                    enriched_map[lever_id].update({k: str(char.get(k, "")) for k in ENRICH_KEYS})
                else:
                    ctx.log(f"LLM returned characterization for an unknown lever_id: '{lever_id}'")
                    errors.append({"type": "ignored_unknown_lever_id", "lever_id": lever_id})

    batches = [levers[i:i + BATCH_SIZE] for i in range(0, len(levers), BATCH_SIZE)]
    # Batches are independent (each sees the full lever list), so they run concurrently.
    ctx.map(lambda b: process(b, 0), batches)

    characterized = []
    for lever_id, data in enriched_map.items():
        if all(k in data for k in ENRICH_KEYS):
            characterized.append({k: data[k] for k in INPUT_KEYS + ENRICH_KEYS})
        else:
            ctx.log(f"Characterization incomplete for lever '{lever_id}'. Skipping this lever.")
            errors.append({"type": "incomplete", "lever_id": lever_id})

    if not characterized:
        # PlanExe would write an empty list and let the next stage fail; fail here instead.
        raise RuntimeError(f"no lever could be characterized: {errors}")
    out = {"metadata": all_metadata, "errors": errors, "characterized_levers": characterized}
    ctx.write_text("enriched_levers_raw.json", json.dumps(out, indent=2))
