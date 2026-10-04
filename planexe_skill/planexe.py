"""Helpers shared by skills to mimic PlanExe's output conventions."""
from __future__ import annotations

import json
import math
from typing import Any

from planexe_skill.llm.base import LLMResult

CONTEXT_WINDOWS = {"sonnet": 1_000_000, "opus": 1_000_000, "haiku": 200_000}


def planexe_metadata(result: LLMResult) -> dict:
    """The `metadata` block PlanExe writes into every *_raw.json file."""
    model = str(result.metadata.get("model", "unknown"))
    ctx = next((v for k, v in CONTEXT_WINDOWS.items() if k in model), 200_000)
    return {
        "context_window": ctx,
        "num_output": 64000,
        "is_chat_model": True,
        "is_function_calling_model": True,
        "model_name": model,
        "system_role": "system",
        "llm_classname": f"{result.metadata.get('backend', 'claude')}_cli",
        "duration": int(math.ceil(float(result.metadata.get("duration_seconds") or 0))),
        "response_byte_count": len((result.text or "").encode("utf-8")),
    }


def raw_document(response: dict, result: LLMResult, system_prompt: str, user_prompt: str) -> dict:
    """PlanExe's common raw layout: response fields + metadata + system_prompt + user_prompt."""
    d = dict(response)
    d["metadata"] = planexe_metadata(result)
    d["system_prompt"] = system_prompt
    d["user_prompt"] = user_prompt
    return d


def structured(ctx, system_prompt: str, user_prompt: str, schema: dict, tier: str | None = None,
               label: str = "") -> tuple[dict, LLMResult]:
    """One structured LLM call. Returns (parsed_response, LLMResult)."""
    result = ctx.llm(system=system_prompt, user=user_prompt, schema=schema, tier=tier, label=label)
    if not isinstance(result.data, dict):
        raise ValueError(f"expected a JSON object from the model, got: {str(result.text)[:300]}")
    return result.data, result


def format_json_for_query(obj: Any) -> str:
    """Compact JSON for embedding in prompts (PlanExe's format_json_for_use_in_query):
    drops metadata/query/user_prompt/system_prompt keys from a top-level dict."""
    if isinstance(obj, dict):
        obj = {k: v for k, v in obj.items() if k not in ("metadata", "query", "user_prompt", "system_prompt")}
    elif not isinstance(obj, list):
        raise TypeError("Input must be a dictionary or a list")
    return json.dumps(obj, separators=(",", ":"))
