"""The plan's purpose (identify_purpose_raw.json) and the system prompt it selects.

PlanExe has three purposes: business, personal, other. PlanExe2 also records a business plan's profit_motive:
- for_profit: run to make a profit for its owners.
- non_profit: run by or as a non-profit (an NGO, a charity, an industry consortium establishing a shared standard,
  a community-run open-source project).
- other: fits neither (a government programme, an agreement between countries, a public-private hybrid).

The LLM sees every business plan as "business", as PlanExe always did: one base prompt per purpose
(`business`, `personal`, `other`). Only a non_profit or other business plan gets a short addendum appended to the
business prompt (`business_non_profit_addendum`, `business_other_addendum`) that says what differs.
"""
from __future__ import annotations

PURPOSES = ("business", "personal", "other")
PROFIT_MOTIVES = ("for_profit", "non_profit", "other")
ADDENDA = ("business_non_profit", "business_other")


def check_purpose(identify_purpose_dict: dict, action: str) -> str:
    """The plan's purpose, the name of its base prompt."""
    purpose = (identify_purpose_dict or {}).get("purpose")
    if purpose not in PURPOSES:
        raise ValueError(f"Invalid purpose: {purpose}, must be one of {', '.join(PURPOSES)}. Cannot {action}.")
    return purpose


def addendum(identify_purpose_dict: dict) -> str | None:
    """`business_non_profit` or `business_other` for a business plan with that profit_motive, else None. A business
    plan without a valid profit_motive is for profit, as PlanExe treats every business plan."""
    d = identify_purpose_dict or {}
    if d.get("purpose") == "business" and d.get("profit_motive") in ("non_profit", "other"):
        return f"business_{d['profit_motive']}"
    return None


def system_prompt(ctx, identify_purpose_dict: dict, action: str, pattern: str = "prompts/{}.md") -> str:
    """The base prompt for the purpose, plus the addendum for a non_profit or other business plan."""
    text = ctx.skill_file(pattern.format(check_purpose(identify_purpose_dict, action))).strip()
    extra = addendum(identify_purpose_dict)
    if extra:
        text += "\n\n" + ctx.skill_file(pattern.format(f"{extra}_addendum")).strip()
    return text
