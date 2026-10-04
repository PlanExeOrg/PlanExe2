"""Shared logic for the six governance phase stages (PlanExe: worker_plan_internal/governance/
governance_phase*.py and plan/nodes/governance_phase*.py).

Every phase is one structured LLM call: system prompt `prompts/system.md` (stripped, as PlanExe
does), user prompt = a list of "File '<label>':\n<content>" sections joined by blank lines,
schema `schema.json`. The raw output is the response + metadata + system_prompt + user_prompt;
the markdown is rendered by the phase's own `to_markdown(response)`.

The first four sections are the same for every phase; the rest differ per phase.
"""
from __future__ import annotations

from typing import Callable

from planexe_skill.planexe import format_json_for_query, raw_document, structured

# The claude CLI gives up with this error when the model's JSON repeatedly fails schema validation
# (seen with Haiku on the long phase-3 step lists). It is not in the backend's transient list, so
# the call is retried here once more before failing the stage.

# (label shown to the model, filename, kind) -- kind "text" embeds the file as-is,
# kind "json" embeds the compacted JSON (format_json_for_use_in_query).
COMMON_SECTIONS: list[tuple[str, str, str]] = [
    ("initial-plan.txt", "plan.txt", "text"),
    ("strategic_decisions.md", "strategic_decisions.md", "text"),
    ("scenarios.md", "scenarios.md", "text"),
    ("assumptions.md", "consolidate_assumptions_short.md", "text"),
]


def build_query(ctx, sections: list[tuple[str, str, str]]) -> str:
    parts = []
    for label, filename, kind in sections:
        if kind == "json":
            content = format_json_for_query(ctx.read_json(filename))
        else:
            content = ctx.read_text(filename)
        parts.append(f"File '{label}':\n{content}")
    return "\n\n".join(parts)


def run_phase(ctx, stage: str, extra_sections: list[tuple[str, str, str]],
              to_markdown: Callable[[dict], str]) -> None:
    """Run one governance phase and write `<stage>_raw.json` and `<stage>.md`."""
    user_prompt = build_query(ctx, COMMON_SECTIONS + extra_sections)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    schema = ctx.skill_json("schema.json")
    # Transient failures (incl. structured_output_retry_exhausted) are retried by the backend.
    response, result = structured(ctx, system_prompt, user_prompt, schema)
    ctx.write_json(f"{stage}_raw.json", raw_document(response, result, system_prompt, user_prompt))
    ctx.write_text(f"{stage}.md", to_markdown(response))
