"""Shared logic for the constraint-checker stages (PlanExe: diagnostics/constraint_checker.py and
plan/nodes/constraint_checker_stages.py).

Given the extracted constraints and a pipeline stage's JSON output, one structured LLM call checks
each constraint (positive/negative, with synonym detection for banned concepts) and returns
satisfied/violated/unclear per constraint plus an overall pass/fail.

Used by the five *_constraint skills and, per lever, by potential_levers.
"""
from __future__ import annotations

import json

from planexe_skill.planexe import planexe_metadata, structured

# Verbatim from PlanExe (CONSTRAINT_CHECKER_SYSTEM_PROMPT, stripped as PlanExe does).
SYSTEM_PROMPT = """You are an expert at verifying whether project plan outputs respect user-specified constraints. You will receive:

1. A list of CONSTRAINTS the user specified (each classified as "positive" or "negative")
2. The JSON output of a pipeline stage

Your job is to check each constraint against the stage output and determine if it is satisfied, violated, or unclear.

CONSTRAINT TYPES:
- **Positive constraints** are things the user WANTS. Check that the stage output is aligned with or supportive of them. A positive constraint is "satisfied" if the output doesn't contradict it. It is "violated" only if the output actively works against it.
- **Negative constraints** are things the user wants to AVOID. This is the critical check. A negative constraint is "violated" if the banned item appears in the output as a recommendation, option, lever, scenario element, or positive suggestion. The banned item should NOT appear in the plan at all except in explicit exclusion notes.

CHECKING RULES:
- For each constraint, look through the entire stage output for mentions of the constrained item.
- For negative constraints: if a banned word/technology/concept appears as a lever name, option, recommendation, or positive element, that is a VIOLATION.
- For negative constraints: if a banned item is mentioned only in the context of "this was excluded" or "this was avoided", that is NOT a violation.
- For positive constraints: only mark as "violated" if the output actively contradicts the constraint. If the constraint simply isn't mentioned, mark as "unclear" rather than "violated".
- Provide specific evidence (quote the relevant text from the stage output) for each assessment.

SYNONYM AND CONCEPT DETECTION (CRITICAL):
- Do NOT just check for exact word matches. Check for SYNONYMS, related concepts, and rebranded terms.
- Examples of synonym violations for negative constraints:
  - "blockchain" also covers: distributed ledger, DLT, web3, smart contracts, on-chain, decentralized ledger
  - "VR" also covers: virtual reality, immersive headset, head-mounted display, VR headset
  - "AR" also covers: augmented reality, mixed reality, AR overlay, AR glasses
  - "NFT" also covers: non-fungible token, digital collectible, tokenized asset
  - "crypto" also covers: cryptocurrency, digital currency, token economy, crypto wallet
  - "DAO" also covers: decentralized autonomous organization, on-chain governance
- If the stage output uses a synonym or closely related concept of a banned item, that is STILL A VIOLATION. The user banned the concept, not just the exact word.
- Use your domain knowledge to identify when a concept is being smuggled in under a different name.

OVERALL STATUS:
- "pass" if zero constraints have status "violated"
- "fail" if one or more constraints have status "violated"

Respond ONLY with a valid JSON object matching the ConstraintCheckResult schema."""

# Verbatim pydantic JSON schema of PlanExe's ConstraintCheckResult.
SCHEMA = {
    "$defs": {
        "ConstraintViolationItem": {
            "description": "Assessment of a single constraint against a pipeline stage output.",
            "properties": {
                "constraint_text": {
                    "description": "The original constraint text being checked.",
                    "title": "Constraint Text",
                    "type": "string"
                },
                "constraint_classification": {
                    "description": "Whether this is a positive or negative constraint.",
                    "enum": [
                        "positive",
                        "negative"
                    ],
                    "title": "Constraint Classification",
                    "type": "string"
                },
                "status": {
                    "description": "'satisfied' if the constraint is respected in the stage output. 'violated' if the constraint is broken (e.g., a banned word appears as a recommendation). 'unclear' if there is not enough information to determine.",
                    "enum": [
                        "satisfied",
                        "violated",
                        "unclear"
                    ],
                    "title": "Status",
                    "type": "string"
                },
                "evidence": {
                    "description": "A short quote or reference from the stage output that supports the status assessment.",
                    "title": "Evidence",
                    "type": "string"
                },
                "explanation": {
                    "description": "1-2 sentence explanation of why this constraint is satisfied, violated, or unclear.",
                    "title": "Explanation",
                    "type": "string"
                }
            },
            "required": [
                "constraint_text",
                "constraint_classification",
                "status",
                "evidence",
                "explanation"
            ],
            "title": "ConstraintViolationItem",
            "type": "object"
        }
    },
    "description": "Structured output for constraint checking of a pipeline stage.",
    "properties": {
        "constraint_violations": {
            "description": "Assessment of each constraint against the stage output.",
            "items": {
                "$ref": "#/$defs/ConstraintViolationItem"
            },
            "title": "Constraint Violations",
            "type": "array"
        },
        "overall_status": {
            "description": "'pass' if no constraints are violated. 'fail' if one or more constraints are violated.",
            "enum": [
                "pass",
                "fail"
            ],
            "title": "Overall Status",
            "type": "string"
        },
        "summary": {
            "default": "",
            "description": "Optional 1-3 sentence summary of the constraint check results.",
            "title": "Summary",
            "type": "string"
        }
    },
    "required": [
        "constraint_violations",
        "overall_status"
    ],
    "title": "ConstraintCheckResult",
    "type": "object"
}


def read_constraints_json(ctx, raw_name: str = "extract_constraints_raw.json") -> str:
    """Only the constraints list of extract_constraints (PlanExe's _read_constraints_json)."""
    raw = ctx.read_json(raw_name)
    return json.dumps({"constraints": raw.get("constraints", [])}, indent=2)


def check(ctx, constraints_json: str, stage_output_json: str, stage_name: str, label: str = "") -> dict:
    """One ConstraintChecker.execute call. Returns PlanExe's to_dict(): the response fields
    (constraint_violations, overall_status, summary) + metadata + system_prompt + user_prompt."""
    user_prompt = (
        f"## Constraints\n{constraints_json}\n\n"
        f"## Stage Output ({stage_name})\n{stage_output_json}"
    )
    response, result = structured(ctx, SYSTEM_PROMPT, user_prompt, SCHEMA, label=label or stage_name)
    response = normalize(response)
    metadata = planexe_metadata(result)
    metadata["stage_name"] = stage_name
    d = dict(response)
    d["metadata"] = metadata
    d["system_prompt"] = SYSTEM_PROMPT
    d["user_prompt"] = user_prompt
    return d


def normalize(response: dict) -> dict:
    """Mirror ConstraintCheckResult.model_dump(): fixed keys, `summary` defaults to ""."""
    items = []
    for v in response.get("constraint_violations") or []:
        items.append({
            "constraint_text": str(v.get("constraint_text", "")),
            "constraint_classification": v.get("constraint_classification"),
            "status": v.get("status"),
            "evidence": str(v.get("evidence", "")),
            "explanation": str(v.get("explanation", "")),
        })
    return {
        "constraint_violations": items,
        "overall_status": response.get("overall_status"),
        "summary": response.get("summary") or "",
    }


def run_stage(ctx, input_name: str, stage_name: str, output_name: str) -> None:
    """The body shared by the *_constraint stages: check `input_name` (read verbatim) and save raw."""
    constraints_json = read_constraints_json(ctx)
    stage_output_json = ctx.read_text(input_name)
    d = check(ctx, constraints_json, stage_output_json, stage_name)
    ctx.write_text(output_name, json.dumps(d, indent=2))
