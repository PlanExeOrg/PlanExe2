import json
from uuid import uuid4

from planexe_skill.planexe import raw_document, structured
from planexe_skill.shared.documents import select_system_prompt

CREATE_KEYS = ("document_name", "description", "responsible_role_type", "document_template_primary",
               "document_template_secondary", "steps_to_create", "approval_authorities")
FIND_KEYS = ("document_name", "description", "recency_requirement", "responsible_role_type", "steps_to_find",
             "access_difficulty")
OPTIONAL_KEYS = {"document_template_primary", "document_template_secondary", "approval_authorities",
                 "recency_requirement"}
LIST_KEYS = {"steps_to_create", "steps_to_find"}


def normalize_item(item: dict, keys: tuple) -> dict:
    """Like pydantic model_dump(): every field present, optional ones default to None."""
    out = {}
    for key in keys:
        value = item.get(key) if isinstance(item, dict) else None
        if key in LIST_KEYS:
            out[key] = [str(x) for x in value] if isinstance(value, list) else ([] if value is None else [str(value)])
        elif key in OPTIONAL_KEYS:
            out[key] = None if value is None else str(value)
        else:
            out[key] = "" if value is None else str(value)
    return out


def convert_to_markdown(documents_to_create: list[dict], documents_to_find: list[dict]) -> str:
    rows = []
    rows.append("\n## Documents to Create\n")
    if documents_to_create:
        for i, item in enumerate(documents_to_create, start=1):
            if i > 1:
                rows.append("")
            rows.append(f"### {i}. {item['document_name']}")
            rows.append(f"\n**ID:** {item['id']}")
            rows.append(f"\n**Description:** {item['description']}")
            rows.append(f"\n**Responsible Role Type:** {item['responsible_role_type']}")
            if item["document_template_primary"]:
                rows.append(f"\n**Primary Template:** {item['document_template_primary']}")
            if item["document_template_secondary"]:
                rows.append(f"\n**Secondary Template:** {item['document_template_secondary']}")
            rows.append("\n**Steps:**\n")
            if item["steps_to_create"]:
                for step in item["steps_to_create"]:
                    rows.append(f"- {step}")
            else:
                rows.append("- *(No steps provided)*")
            if item["approval_authorities"]:
                rows.append(f"\n**Approval Authorities:** {item['approval_authorities']}")
    else:
        rows.append("\n*No documents identified to create.*")

    rows.append("\n## Documents to Find\n")
    if documents_to_find:
        for i, item in enumerate(documents_to_find, start=1):
            if i > 1:
                rows.append("")
            rows.append(f"### {i}. {item['document_name']}")
            rows.append(f"\n**ID:** {item['id']}")
            rows.append(f"\n**Description:** {item['description']}")
            if item["recency_requirement"]:
                rows.append(f"\n**Recency Requirement:** {item['recency_requirement']}")
            rows.append(f"\n**Responsible Role Type:** {item['responsible_role_type']}")
            rows.append(f"\n**Access Difficulty:** {item['access_difficulty']}")
            rows.append("\n**Steps:**\n")
            if item["steps_to_find"]:
                for step in item["steps_to_find"]:
                    rows.append(f"- {step}")
            else:
                rows.append("- *(No steps provided)*")
    else:
        rows.append("\n*No documents identified to find.*")
    return "\n".join(rows)


def run(ctx):
    identify_purpose_dict = ctx.read_json("identify_purpose_raw.json")
    query = (
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'assumptions.md':\n{ctx.read_text('consolidate_assumptions_short.md')}\n\n"
        f"File 'project-plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"File 'related-resources.md':\n{ctx.read_text('related_resources.md')}\n\n"
        f"File 'swot-analysis.md':\n{ctx.read_text('swot_analysis.md')}\n\n"
        f"File 'team.md':\n{ctx.read_text('team.md')}\n\n"
        f"File 'expert-review.md':\n{ctx.read_text('expert_criticism.md')}"
    )
    system_prompt = select_system_prompt(ctx, identify_purpose_dict, "identify documents")
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))

    details = {}
    for key, keys in (("documents_to_create", CREATE_KEYS), ("documents_to_find", FIND_KEYS),
                      ("documents_to_create_part2", CREATE_KEYS), ("documents_to_find_part2", FIND_KEYS)):
        details[key] = [normalize_item(item, keys) for item in (response.get(key) or [])]

    # Cleanup: combine part1 and part2, assign a unique id to each document.
    documents_to_create = [{"id": str(uuid4()), **item}
                           for item in details["documents_to_create"] + details["documents_to_create_part2"]]
    documents_to_find = [{"id": str(uuid4()), **item}
                         for item in details["documents_to_find"] + details["documents_to_find_part2"]]

    ctx.write_text("identified_documents_raw.json",
                   json.dumps(raw_document(details, result, system_prompt, query), indent=2))
    ctx.write_text("identified_documents.md", convert_to_markdown(documents_to_create, documents_to_find))
    ctx.write_text("identified_documents_to_find.json", json.dumps(documents_to_find, indent=2))
    ctx.write_text("identified_documents_to_create.json", json.dumps(documents_to_create, indent=2))
