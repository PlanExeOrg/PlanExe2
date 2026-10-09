"""Make calendar dates in LLM output agree with the project start date.

Models without reasoning are bad at calendar arithmetic ("Month 72 (February 2033)" for a May 2026
start). The month offset is the plan's own logic; the calendar date is derived, so it is computed
mechanically (date = start + N months, fractional months allowed) and never trusted from the model:

1. dates the model wrote next to a "Month N" (either order) are recomputed, keeping its date style;
   fuzzy forms ("mid-July 2026") become an exact ISO date;
2. every remaining bare "Month N" / "Months A-B" gets its date(s) appended: "Month 3 (2026-08-02)".

Prompts additionally ask models to write time as "Month N" only; dates without a month offset
("through February 2033") can't be checked mechanically.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
_MONTH_RX = "|".join(MONTHS + [m[:3] for m in MONTHS])
_N = r"(?P<n>\d{1,3}(?:\.\d+)?)"
_NOT_RANGE = r"(?!\d|\.\d|\s*(?:[-–]|to)\s*\d)"
_DATE = (r"(?P<date>(?P<fuzzy>(?:early|mid|late)[- ])?(?P<mname>" + _MONTH_RX + r")\.?(?:\s+(?P<day>\d{1,2}),?)?"
         r"\s+(?P<y1>\d{4})|(?P<y2>\d{4})-(?P<m2>\d{2})(?:-(?P<d2>\d{2}))?)")
_DATE_NAMED = (r"(?P<date>(?P<fuzzy>(?:early|mid|late)[- ])?(?P<mname>" + _MONTH_RX + r")\.?"
               r"(?:\s+(?P<day>\d{1,2}),?)?\s+(?P<y1>\d{4}))")

# "Month 24 (April 30, 2028" / "month 24, April 2028" / "Month 3 (2026-07" / "month 18 = May 2028" /
# "month 24 gate (April 2028" / "month 3.5 (mid-July 2026"
_PAIR = re.compile(
    r"(?P<lead>\b(?:[Mm]onth|M)\s?" + _N + _NOT_RANGE + r"(?:\s+[A-Za-z][\w-]{1,15})?"
    r"\s*(?:\(|,\s*|:\s*|—\s*|-\s+|~\s*|≈\s*|=\s*|is\s+))" + _DATE)
# Reverse order: "July 2, 2026 (month 3" / "August 2026, month 4"
_REVERSE = re.compile(r"(?<!\x01)" + _DATE_NAMED + r"(?P<trail>\s*(?:\(|,\s*)\s*[Mm]onth\s?" + _N + _NOT_RANGE + r")")
# Bare offsets not already followed by a date.
_FOLLOWED_BY_DATE = (r"(?!(?:\s+[A-Za-z][\w-]{1,15})?\s*(?:\(|,|:|—|=|~|≈)?\s*"
                     r"(?:\d{4}-\d{2}|(?:early|mid|late)[- ]|(?:" + _MONTH_RX + r")\b))")
_RANGE = re.compile(r"\b[Mm]onths?\s?(?P<a>\d{1,3}(?:\.\d+)?)\s*(?:[-–]|to)\s*(?P<b>\d{1,3}(?:\.\d+)?)(?!\d|\.\d)"
                    + _FOLLOWED_BY_DATE)
# "months 18, 36, 54, 72" / "months 6 and 12"
_LIST_SEP = r"\s*(?:,\s*(?:and|or)?|and|or|&|/)\s*"
_LIST = re.compile(r"\b[Mm]onths?\s?(?P<items>\d{1,3}(?:\.\d+)?(?:" + _LIST_SEP + r"\d{1,3}(?:\.\d+)?)+)\b"
                   r"(?!\s*(?:[-–]|to)\s*\d|\+|\.\d|" + _LIST_SEP + r"\d)" + _FOLLOWED_BY_DATE)
# A later list item followed by this is a quantity, not a month: "Month 8, 80/month", "Month 6.5, 100%",
# "Month 2, 40 by Month 3".
_QUANTITY_AFTER = re.compile(r"\s*%|\s*/\s*[A-Za-z]|\s+per\b|\s+(?:by|in|at|from|until|before|after)\s+[Mm]onths?\b")
# A stale date-only parenthetical right after a computed date: "(2030-05-02 to 2032-05-02) (through February 2033)"
_STALE_AFTER = re.compile(r"(?P<keep>\(\d{4}-\d{2}-\d{2}(?: to \d{4}-\d{2}-\d{2})?\))\s*\((?:through|by|until|to|ending|ends|"
                          r"from|in|approx\.?|about|~|≈)?\s*(?:early|mid|late)?[- ]?(?:" + _MONTH_RX +
                          r")\.?(?:\s+\d{1,2},?)?\s+\d{4}\)")
# Not part of a list ("Month 0.5, 1, 1.5" / "Month 0.5 or 2" are handled by _LIST) and not "Month 13+".
_BARE = re.compile(r"\b[Mm]onth\s?" + _N + _NOT_RANGE + r"\b(?!\+|" + _LIST_SEP + r"\d)" + _FOLLOWED_BY_DATE)


def add_months(start: date, n: int) -> date:
    y, m = start.year + (start.month - 1 + n) // 12, (start.month - 1 + n) % 12 + 1
    dim = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31,
           30, 31][m - 1]
    return date(y, m, min(start.day, dim))


def offset_date(start: date, n: float) -> date:
    whole = int(n)
    return add_months(start, whole) + timedelta(days=round((n - whole) * 30.44))


def _styled(d: date, m: re.Match) -> str:
    gd = m.groupdict()
    if gd.get("fuzzy"):
        return d.isoformat()
    if gd.get("mname"):
        mname = MONTHS[d.month - 1] if gd["mname"] in MONTHS else MONTHS[d.month - 1][:3]
        if gd.get("day"):
            return f"{mname} {d.day}, {d.year}"
        return f"{mname}, {d.year}" if "," in gd["date"] else f"{mname} {d.year}"
    return f"{d.year:04d}-{d.month:02d}" + (f"-{d.day:02d}" if gd.get("d2") else "")


def fix_text(text: str, start: date, annotate: bool = True) -> tuple[str, int]:
    count = 0

    def in_range(n: float) -> bool:
        return 0 <= n <= 240

    def repl(m: re.Match) -> str:
        nonlocal count
        n = float(m.group("n"))
        if not in_range(n):
            return m.group(0)
        new = _styled(offset_date(start, n), m)
        count += new != m.group("date")
        return m.group("lead") + "\x01" + new  # marker: this date is taken, the reverse rule must skip it

    def repl_reverse(m: re.Match) -> str:
        nonlocal count
        n = float(m.group("n"))
        if not in_range(n):
            return m.group(0)
        new = _styled(offset_date(start, n), m)
        count += new != m.group("date")
        return new + m.group("trail")

    def inside_parens(m: re.Match) -> bool:
        line_start = m.string.rfind("\n", 0, m.start()) + 1
        before = m.string[line_start:m.start()]
        return before.count("(") > before.count(")")

    def annotated(m: re.Match, dates: str, text: str | None = None) -> str:
        # Inside an existing parenthesis use "= date" to avoid nested "( ... (date) ... )".
        text = m.group(0) if text is None else text
        return f"{text} = {dates}" if inside_parens(m) else f"{text} ({dates})"

    def repl_range(m: re.Match) -> str:
        nonlocal count
        a, b = float(m.group("a")), float(m.group("b"))
        if not (in_range(a) and in_range(b)) or a >= b:
            return m.group(0)
        count += 1
        return annotated(m, f"{offset_date(start, a).isoformat()} to {offset_date(start, b).isoformat()}")

    def repl_list(m: re.Match) -> str:
        nonlocal count
        items = list(re.finditer(r"\d{1,3}(?:\.\d+)?", m.group("items")))
        for i, item in enumerate(items[1:], 1):
            if _QUANTITY_AFTER.match(m.string, m.start("items") + item.end()):
                items = items[:i]  # the list ends before the quantity
                break
        nums = [float(item.group()) for item in items]
        if not all(in_range(n) for n in nums):
            return m.group(0)
        count += 1
        cut = m.start("items") + items[-1].end() - m.start()
        dates = ", ".join(offset_date(start, n).isoformat() for n in nums)
        return annotated(m, dates, m.group(0)[:cut]) + m.group(0)[cut:]

    def repl_bare(m: re.Match) -> str:
        nonlocal count
        n = float(m.group("n"))
        if not in_range(n):
            return m.group(0)
        count += 1
        return annotated(m, offset_date(start, n).isoformat())

    text = _PAIR.sub(repl, text)
    text = _REVERSE.sub(repl_reverse, text).replace("\x01", "")
    if annotate:
        text = _RANGE.sub(repl_range, text)
        text = _LIST.sub(repl_list, text)
        text = _BARE.sub(repl_bare, text)
    text, stale = _STALE_AFTER.subn(lambda m: m.group("keep"), text)
    return text, count + stale


def fix_value(value: Any, start: date, annotate: bool = True) -> tuple[Any, int]:
    """Apply fix_text to every string inside a JSON-like value."""
    if isinstance(value, str):
        return fix_text(value, start, annotate)
    if isinstance(value, list):
        out, total = [], 0
        for v in value:
            fv, c = fix_value(v, start, annotate)
            out.append(fv)
            total += c
        return out, total
    if isinstance(value, dict):
        out, total = {}, 0
        for k, v in value.items():
            fv, c = fix_value(v, start, annotate)
            out[k] = fv
            total += c
        return out, total
    return value, 0
