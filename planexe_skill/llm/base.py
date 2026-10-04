"""LLM backend interface shared by all backends."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class LLMError(Exception):
    """An LLM call failed. The message is meant to be read by a human."""


@dataclass
class LLMResult:
    data: Any                 # parsed structured output (dict) or None for free text
    text: str                 # raw text returned by the model
    metadata: dict = field(default_factory=dict)  # model, duration, tokens, cost...


class Backend:
    name = "base"

    def complete(self, system: str, user: str, schema: dict | None = None, tier: str = "low") -> LLMResult:
        raise NotImplementedError

    def model_for(self, tier: str) -> str:
        return "unknown"
