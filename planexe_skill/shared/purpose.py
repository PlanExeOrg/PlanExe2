"""The plan's purpose (identify_purpose_raw.json) and the prompt variant it selects.

PlanExe has three purposes: business, personal, other. PlanExe2 splits business by profit_motive:
- for_profit: run to make a profit for its owners.
- non_profit: run by or as a non-profit (an NGO, a charity, an industry consortium establishing a shared standard,
  an open-source project).
- other: fits neither (a government programme, an agreement between countries, a public-private hybrid).
Each gets its own prompt variant: business_for_profit, business_non_profit, business_other.
"""
from __future__ import annotations

PURPOSES = ("business", "personal", "other")
PROFIT_MOTIVES = ("for_profit", "non_profit", "other")
PROMPT_VARIANTS = ("business_for_profit", "business_non_profit", "business_other", "personal", "other")


def prompt_variant(identify_purpose_dict: dict, action: str) -> str:
    """The prompt variant for identify_purpose_raw.json (see module doc). A business plan without a valid
    profit_motive is treated as for_profit, as PlanExe treats every business plan."""
    d = identify_purpose_dict or {}
    purpose = d.get("purpose")
    if purpose not in PURPOSES:
        raise ValueError(f"Invalid purpose: {purpose}, must be one of {', '.join(PURPOSES)}. Cannot {action}.")
    if purpose == "business":
        motive = d.get("profit_motive")
        return f"business_{motive if motive in PROFIT_MOTIVES else 'for_profit'}"
    return purpose
