"""Deterministic backend for tests and dry runs."""
from __future__ import annotations

import json
from typing import Any, Callable

from planexe_skill.llm.base import Backend, LLMResult


def _example_from_schema(schema: dict) -> Any:
    t = schema.get("type")
    if "enum" in schema:
        return schema["enum"][0]
    if t == "object":
        return {k: _example_from_schema(v) for k, v in schema.get("properties", {}).items()}
    if t == "array":
        return [_example_from_schema(schema.get("items", {"type": "string"}))]
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "boolean":
        return True
    return "text"


class FakeBackend(Backend):
    name = "fake"

    def __init__(self, responder: Callable[[str, str, dict | None, str], Any] | None = None):
        self.responder = responder
        self.calls: list[dict] = []

    def model_for(self, tier: str) -> str:
        return f"fake-{tier}"

    def complete(self, system: str, user: str, schema: dict | None = None, tier: str = "low",
                 web_search: bool = False) -> LLMResult:
        self.calls.append({"system": system, "user": user, "schema": schema, "tier": tier, "web_search": web_search})
        if self.responder is not None:
            data = self.responder(system, user, schema, tier)
        elif schema is not None:
            data = _example_from_schema(schema)
        else:
            data = "fake response"
        text = data if isinstance(data, str) else json.dumps(data)
        return LLMResult(data=None if isinstance(data, str) and schema is None else data, text=text,
                         metadata={"model": self.model_for(tier), "backend": "fake", "duration_seconds": 0.0,
                                   "input_tokens": 0, "output_tokens": 0, "cost_usd": 0})
