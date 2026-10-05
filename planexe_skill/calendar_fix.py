"""Make 'Month N (date)' pairs in LLM output agree with the project start date.

Models without reasoning are bad at calendar arithmetic ("Month 72 (February 2033)" for a May 2026
start). The month number is the plan's own logic; the calendar date is derived, so we recompute it
mechanically: date = start + N months, written in the same style the model used.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
_MONTH_RX = "|".join(MONTHS + [m[:3] for m in MONTHS])

# "Month 24 (April 30, 2028" / "month 24, April 2028" / "Month 3 (2026-07" / "M24 (Apr 2028" /
# "month 18 = May 2028" / "month 24 gate (April 2028"
_PAIR = re.compile(
    r"(?P<lead>\b(?:[Mm]onth|M)\s?(?P<n>\d{1,3})(?!\d|\s*[-–]\s*\d)(?:\s+[A-Za-z][\w-]{1,15})?"
    r"\s*(?:\(|,\s*|:\s*|—\s*|-\s+|~\s*|≈\s*|=\s*|is\s+))"
    r"(?P<date>(?P<mname>" + _MONTH_RX + r")\.?(?:\s+(?P<day>\d{1,2}),?)?\s+(?P<y1>\d{4})"
    r"|(?P<y2>\d{4})-(?P<m2>\d{2})(?:-(?P<d2>\d{2}))?)")


# Reverse order: "July 2, 2026 (month 3" / "August 2026, month 4" / "March 31, 2027, Month 12"
_REVERSE = re.compile(
    r"(?P<date>(?P<mname>" + _MONTH_RX + r")\.?(?:\s+(?P<day>\d{1,2}),?)?\s+(?P<y1>\d{4}))"
    r"(?P<trail>\s*(?:\(|,\s*|;\s*)\s*[Mm]onth\s?(?P<n>\d{1,3})\b(?!\s*[-–]\s*\d))")


def add_months(start: date, n: int) -> date:
    y, m = start.year + (start.month - 1 + n) // 12, (start.month - 1 + n) % 12 + 1
    dim = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31,
           30, 31][m - 1]
    return date(y, m, min(start.day, dim))


def fix_text(text: str, start: date) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        n = int(m.group("n"))
        if n > 240:
            return m.group(0)
        d = add_months(start, n)
        if m.group("mname"):
            name = m.group("mname")
            full = name in MONTHS  # "May" is a full name, not an abbreviation
            mname = MONTHS[d.month - 1] if full else MONTHS[d.month - 1][:3]
            new = f"{mname} {d.day}, {d.year}" if m.group("day") else f"{mname} {d.year}"
            if not m.group("day") and "," in m.group("date"):
                new = f"{mname}, {d.year}"
        else:
            new = f"{d.year:04d}-{d.month:02d}" + (f"-{d.day:02d}" if m.group("d2") else "")
        if new != m.group("date"):
            count += 1
        return m.group("lead") + new

    def repl_reverse(m: re.Match) -> str:
        nonlocal count
        n = int(m.group("n"))
        if n > 240:
            return m.group(0)
        d = add_months(start, n)
        name = m.group("mname")
        mname = MONTHS[d.month - 1] if name in MONTHS else MONTHS[d.month - 1][:3]
        new = f"{mname} {d.day}, {d.year}" if m.group("day") else f"{mname} {d.year}"
        if new != m.group("date"):
            count += 1
        return new + m.group("trail")

    text = _PAIR.sub(repl, text)
    return _REVERSE.sub(repl_reverse, text), count


def fix_value(value: Any, start: date) -> tuple[Any, int]:
    """Apply fix_text to every string inside a JSON-like value."""
    if isinstance(value, str):
        return fix_text(value, start)
    if isinstance(value, list):
        out, total = [], 0
        for v in value:
            fv, c = fix_value(v, start)
            out.append(fv)
            total += c
        return out, total
    if isinstance(value, dict):
        out, total = {}, 0
        for k, v in value.items():
            fv, c = fix_value(v, start)
            out[k] = fv
            total += c
        return out, total
    return value, 0
