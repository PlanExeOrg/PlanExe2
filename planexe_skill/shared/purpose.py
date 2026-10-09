"""The plan's purpose (identify_purpose_raw.json) and the prompt variant it selects.

PlanExe has three purposes: business, personal, other. PlanExe2 adds a profit_motive: for_profit, non_profit
(an NGO, a charity, an industry consortium establishing a shared standard, an open-source project) or other (fits
neither: a government programme, an agreement between countries, a public-private hybrid). A business plan whose
profit_motive is non_profit or other selects the business_non_profit prompt variants: neither is judged by revenue
or return on investment for owners.
"""
from __future__ import annotations

PURPOSES = ("business", "personal", "other")
PROMPT_VARIANTS = ("business", "business_non_profit", "personal", "other")
PROFIT_MOTIVES = ("for_profit", "non_profit", "other")


def prompt_variant(identify_purpose_dict: dict, action: str) -> str:
    """The prompt variant for identify_purpose_raw.json: its purpose, or business_non_profit (see module doc)."""
    d = identify_purpose_dict or {}
    purpose = d.get("purpose")
    if purpose not in PURPOSES:
        raise ValueError(f"Invalid purpose: {purpose}, must be one of {', '.join(PURPOSES)}. Cannot {action}.")
    if purpose == "business" and d.get("profit_motive") in ("non_profit", "other"):
        return "business_non_profit"
    return purpose
