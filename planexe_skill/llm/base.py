"""LLM backend interface shared by all backends."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class LLMError(Exception):
    """An LLM call failed. The message is meant to be read by a human."""


class BackendConfigError(ValueError):
    """The backend can't be built from the given options (e.g. no model). The message is for a human."""


class LLMAuthError(LLMError):
    """Not logged in / credentials revoked: every further call will fail, so the run must stop."""


@dataclass
class LLMResult:
    data: Any                 # parsed structured output (dict) or None for free text
    text: str                 # raw text returned by the model
    metadata: dict = field(default_factory=dict)  # model, duration, tokens, cost...


class Backend:
    name = "base"
    login_hint = "Run 'claude auth login'"  # shown when a call fails with LLMAuthError

    def complete(self, system: str, user: str, schema: dict | None = None, tier: str = "low",
                 web_search: bool = False) -> LLMResult:
        raise NotImplementedError

    def model_for(self, tier: str) -> str:
        return "unknown"
