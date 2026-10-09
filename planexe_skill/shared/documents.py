"""Shared logic for the documents-to-create / documents-to-find stages (PlanExe worker_plan_internal/document/).

Used by identify_documents, filter_documents_to_create, filter_documents_to_find,
draft_documents_to_create and draft_documents_to_find.
"""
from __future__ import annotations

import json

from planexe_skill.planexe import planexe_metadata, raw_document, structured
from planexe_skill.shared.purpose import prompt_variant

# The number of documents to keep. It may be less or greater than this number (PlanExe PREFERRED_DOCUMENT_COUNT).
PREFERRED_DOCUMENT_COUNT = 5

IMPACT_RATINGS = ("Critical", "High", "Medium", "Low")


def select_system_prompt(ctx, identify_purpose_dict: dict, action: str) -> str:
    """Pick the system prompt for identify_purpose_raw.json's purpose (and profit_motive)."""
    return ctx.skill_file(f"prompts/{prompt_variant(identify_purpose_dict, action)}.md").strip()


def documents_query(ctx, document_section: str) -> str:
    """The user prompt shared by the filter/draft stages (assumptions.md = consolidate_assumptions_short.md)."""
    return (
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'assumptions.md':\n{ctx.read_text('consolidate_assumptions_short.md')}\n\n"
        f"File 'project-plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"{document_section}"
    )


# ---------------------------------------------------------------- filter

def process_documents_and_integer_ids(documents: list[dict]) -> tuple[list[dict], dict[int, str]]:
    """Reduce each document to {id: int, name: 'document_name\\ndescription'} (uuids confuse the LLM)."""
    if not isinstance(documents, list):
        raise ValueError("identified_documents_raw_json is not a list.")
    process_documents = []
    integer_id_to_document_uuid = {}
    for doc in documents:
        if "document_name" not in doc or "description" not in doc or "id" not in doc:
            continue
        current_index = len(process_documents)
        process_documents.append({"id": current_index, "name": f"{doc.get('document_name', '')}\n{doc.get('description', '')}"})
        integer_id_to_document_uuid[current_index] = doc.get("id", "")
    return process_documents, integer_id_to_document_uuid


def extract_integer_ids_to_keep(document_list: list[dict]) -> set[int]:
    """Keep all Critical; add High, then Medium, then Low while fewer than PREFERRED_DOCUMENT_COUNT."""
    buckets = {r: set() for r in IMPACT_RATINGS}
    for item in document_list:
        rating = item.get("impact_rating")
        if rating in buckets:
            buckets[rating].add(item.get("id"))
    ids_to_keep: set[int] = set()
    ids_to_keep.update(buckets["Critical"])
    for rating in ("High", "Medium", "Low"):
        if len(ids_to_keep) < PREFERRED_DOCUMENT_COUNT:
            ids_to_keep.update(buckets[rating])
    return ids_to_keep


def run_filter(ctx, input_name: str, raw_name: str, clean_name: str) -> None:
    """FilterDocumentsToCreate / FilterDocumentsToFind (identical code, different prompts)."""
    identify_purpose_dict = ctx.read_json("identify_purpose_raw.json")
    documents = ctx.read_json(input_name)
    process_documents, integer_id_to_document_uuid = process_documents_and_integer_ids(documents)
    # PlanExe embeds the python repr of the list (f"{process_documents}").
    user_prompt = documents_query(ctx, f"File 'documents.json':\n{process_documents}")
    system_prompt = select_system_prompt(ctx, identify_purpose_dict, "filter documents")

    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    document_list = []
    for item in response.get("document_list") or []:
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id.strip().isdigit():
            item_id = int(item_id.strip())
        document_list.append({"id": item_id, "rationale": str(item.get("rationale", "")),
                              "impact_rating": item.get("impact_rating")})
    response = {"document_list": document_list, "summary": str(response.get("summary", ""))}

    ids_to_keep = extract_integer_ids_to_keep(document_list)
    unknown = [i for i in ids_to_keep if i not in integer_id_to_document_uuid]
    if unknown:
        raise ValueError(f"LLM returned unknown document ids: {unknown}")
    uuids_to_keep = {integer_id_to_document_uuid[i] for i in ids_to_keep}
    filtered = [doc for doc in documents if doc["id"] in uuids_to_keep]
    if len(filtered) != len(ids_to_keep):
        raise ValueError("Filtered documents raw json length does not match ids_to_keep length.")
    ctx.log(f"IDs to keep: {sorted(ids_to_keep)}; kept {len(filtered)} of {len(documents)} documents")

    ctx.write_text(raw_name, json.dumps(raw_document(response, result, system_prompt, user_prompt), indent=2))
    ctx.write_text(clean_name, json.dumps(filtered, indent=2))


# ---------------------------------------------------------------- draft

DRAFT_KEYS = ("essential_information", "risks_of_poor_quality", "worst_case_scenario", "best_case_scenario",
              "fallback_alternative_approaches")


def run_draft(ctx, input_name: str, raw_template: str, output_name: str, kind: str) -> None:
    """DraftDocumentsToCreate / DraftDocumentsToFind: one independent call per filtered document."""
    identify_purpose_dict = ctx.read_json("identify_purpose_raw.json")
    documents = ctx.read_json(input_name)
    system_prompt = select_system_prompt(ctx, identify_purpose_dict, f"draft document to {kind}")
    schema = ctx.skill_json("schema.json")
    # Read once (the context files are identical for every document).
    head = documents_query(ctx, "")

    def draft(indexed):
        index, document = indexed
        # PlanExe embeds the python repr of the document dict (f"{document}").
        user_prompt = f"{head}File 'document.json':\n{document}"
        try:
            response, result = structured(ctx, system_prompt, user_prompt, schema,
                                          label=f"document-to-{kind} {index + 1} of {len(documents)}")
        except Exception as e:
            raise ValueError(f"Document-to-{kind} {index + 1} LLM interaction failed.") from e
        response = normalize_draft(response)
        meta = planexe_metadata(result)
        meta.pop("response_byte_count", None)
        raw = dict(response)
        raw["metadata"] = meta
        raw["system_prompt"] = system_prompt
        raw["user_prompt"] = user_prompt
        ctx.write_text(raw_template.format(index + 1), json.dumps(raw, indent=2))
        updated = dict(document)
        updated.update(response)
        return updated

    accumulated = ctx.map(draft, list(enumerate(documents)))
    ctx.write_text(output_name, json.dumps(accumulated, indent=2))


def normalize_draft(response: dict) -> dict:
    """Schema keys first, in schema order, with the right value types."""
    out = {}
    for key in DRAFT_KEYS:
        value = response.get(key)
        if key in ("worst_case_scenario", "best_case_scenario"):
            out[key] = "" if value is None else str(value)
        else:
            out[key] = [str(x) for x in value] if isinstance(value, list) else ([] if value is None else [str(value)])
    for key, value in response.items():
        if key not in out:
            out[key] = value
    return out
