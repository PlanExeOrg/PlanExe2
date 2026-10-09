"""The plan's purpose (identify_purpose_raw.json) and the prompt variant it selects.

PlanExe has three purposes: business, personal, other. PlanExe2 adds a non_profit flag: a business plan that is
not run for profit (a public-sector programme, an NGO, an industry consortium establishing a shared standard, an
open-source project) selects the business_non_profit prompt variants.
"""
from __future__ import annotations

PURPOSES = ("business", "personal", "other")
PROMPT_VARIANTS = ("business", "business_non_profit", "personal", "other")


def prompt_variant(identify_purpose_dict: dict, action: str) -> str:
    """The prompt variant for identify_purpose_raw.json: its purpose, or business_non_profit."""
    d = identify_purpose_dict or {}
    purpose = d.get("purpose")
    if purpose not in PURPOSES:
        raise ValueError(f"Invalid purpose: {purpose}, must be one of {', '.join(PURPOSES)}. Cannot {action}.")
    if purpose == "business" and d.get("non_profit") is True:
        return "business_non_profit"
    return purpose
