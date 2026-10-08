"""Deterministic check of the explicit arithmetic written in plan documents.

LLM-written plans state calculations inline ("4.5 + 6.0 + 6.5 = USD 17B", "18 trips x EUR 30-50 =
EUR 540-900/day", "USD 13.33M/yr = 16.67M m3 x USD 0.80/m3"). This module finds `expression = value`
statements, evaluates the expression and reports the ones whose stated value is wrong.

It is built for precision over recall: anything ambiguous (dates, slash lists such as "Months
36/84", unparseable text, words inside the expression) is skipped rather than guessed, and a
statement passes if any reasonable reading matches (with or without k/M/B multipliers, percent as
x/100 or x, ranges evaluated end-point-wise or as intervals, rounding of the stated value).

Supported: + - x × * / ÷ ^, parentheses, currency prefixes (USD, EUR, $, €, ...), multipliers (k, M,
B, bn, million, billion), percents, ranges ("30-50", "150k–400k", "3.6–9.6M"), units after numbers
("m3/d", "t/yr", "alert days"), chains ("a x b = c x d = e").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MULTIPLIERS = {"k": 1e3, "K": 1e3, "M": 1e6, "mn": 1e6, "B": 1e9, "bn": 1e9,
               "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
CURRENCY_WORDS = {"USD", "EUR", "GBP", "CHF", "DKK", "SEK", "NOK", "JPY", "CNY", "INR", "BRL", "AUD", "CAD",
                  "Rs", "US$", "US"}
APPROX_WORDS = {"about", "approximately", "approx", "roughly", "around", "nearly", "almost", "circa", "ca"}
STOPWORDS = {"and", "or", "but", "so", "vs", "versus", "while", "which", "that", "then", "if", "when", "where",
             "is", "are", "was", "were", "be", "to", "of", "in", "on", "at", "by", "for", "from", "with", "as",
             "the", "a", "an", "this", "these", "it", "its", "not", "no", "per", "plus", "minus", "times",
             "gives", "give", "means", "equals", "total", "totals", "sum", "would", "will", "can", "must",
             "should", "than", "over", "under", "within", "after", "before", "into", "each", "every"}

TOKEN_RE = re.compile(r"""
    (?P<date>\b\d{4}-\d{2}-\d{2}\b)
  | (?P<num>
        (?:(?P<cur>[$€£])\s?)?
        (?P<a>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)
        (?P<am>bn|mn|[kKMB](?![A-Za-z]))?
        (?:(?:\s?[–—]\s?|-(?=[$€£]?\d))[$€£]?
           (?P<b>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)
           (?P<bm>bn|mn|[kKMB](?![A-Za-z]))?)?
        (?P<pct>\s?%)?
    )
  | (?P<op>[+×*÷^−=≈]|/(?![A-Za-z])|(?<=\s)-(?=\s)|\bx\b|\bX\b|(?<=\d)x(?=\d))
  | (?P<lp>\()
  | (?P<rp>\))
  | (?P<word>US\$|[A-Za-z][A-Za-z0-9'³²]*(?:/[A-Za-z0-9³²]+)*|/[A-Za-z][A-Za-z0-9³²]*)
  | (?P<boundary>[;:|,.!?\n—–\[\]{}"“”])
  | (?P<other>\S)
""", re.VERBOSE)


@dataclass
class Num:
    lo: float
    hi: float
    mult_lo: float = 1.0
    mult_hi: float = 1.0
    pct: bool = False
    text: str = ""
    decimals: int = 0
    approx: bool = False

    err: float = 0.0  # rounding uncertainty of the written number (mantissa units)

    def interval(self, use_mult: bool, end: str, with_err: bool) -> tuple[float, float]:
        """The number (end 'lo', 'hi', or 'both' for the whole range), +-err when with_err."""
        e = self.err if with_err else 0.0
        a = self.lo if end in ("lo", "both") else self.hi
        b = self.hi if end in ("hi", "both") else self.lo
        ma = (self.mult_lo if end in ("lo", "both") else self.mult_hi) if use_mult else 1.0
        mb = (self.mult_hi if end in ("hi", "both") else self.mult_lo) if use_mult else 1.0
        d = 100.0 if self.pct else 1.0
        return (a - e) * ma / d, (b + e) * mb / d


@dataclass
class Tok:
    kind: str  # num, op, lp, rp, eq, word, date, unit
    text: str
    start: int
    end: int
    space_before: bool
    num: Num | None = None


@dataclass
class Finding:
    document: str
    line: int
    excerpt: str
    expression: str
    stated: str
    computed: str
    ok: bool
    note: str = ""
    extra: dict = field(default_factory=dict)


def _num_value(s: str) -> float:
    return float(s.replace(",", ""))


def _decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def tokenize(text: str) -> list[Tok]:
    out: list[Tok] = []
    for m in TOKEN_RE.finditer(text):
        sb = m.start() == 0 or text[m.start() - 1].isspace()
        k = m.lastgroup
        if m.group("date"):
            out.append(Tok("date", m.group(0), m.start(), m.end(), sb))
        elif m.group("num") is not None and m.group("a") is not None:
            a, b = m.group("a"), m.group("b")
            am, bm = m.group("am"), m.group("bm")
            lo = _num_value(a)
            hi = _num_value(b) if b else lo
            mlo = MULTIPLIERS.get(am, 1.0) if am else 1.0
            mhi = MULTIPLIERS.get(bm, 1.0) if bm else mlo
            if bm and not am:
                mlo = mhi  # "3.6–9.6M": the multiplier applies to both ends
            if b and lo * mlo > hi * mhi:
                out.append(Tok("word", m.group(0), m.start(), m.end(), sb))  # "13.33-8.33": not a range
                continue
            dec = max(_decimals(a), _decimals(b) if b else 0)
            n = Num(lo, hi, mlo, mhi, bool(m.group("pct")), m.group(0).strip(), dec)
            n.err = _rounding(n)
            out.append(Tok("num", m.group(0).strip(), m.start(), m.end(), sb, n))
        elif m.group("op"):
            t = m.group("op")
            if t in "=≈":
                out.append(Tok("eq", t, m.start(), m.end(), sb))
            else:
                out.append(Tok("op", {"×": "*", "x": "*", "X": "*", "÷": "/", "−": "-"}.get(t, t), m.start(), m.end(), sb))
        elif k == "lp":
            out.append(Tok("lp", "(", m.start(), m.end(), sb))
        elif k == "rp":
            out.append(Tok("rp", ")", m.start(), m.end(), sb))
        elif k == "word":
            out.append(Tok("word", m.group(0), m.start(), m.end(), sb))
        elif k == "boundary":
            t = m.group(0)
            # decimal points and thousands separators are inside number tokens; a lone '.' or ',' is punctuation
            out.append(Tok("boundary", t, m.start(), m.end(), sb))
        else:
            out.append(Tok("other", m.group(0), m.start(), m.end(), sb))
    return _classify(out)


def _classify(toks: list[Tok]) -> list[Tok]:
    """Resolve 'x' (multiply vs unit), multiplier/unit/currency/approx words, slash lists."""
    res: list[Tok] = []
    approx_next = False
    for i, t in enumerate(toks):
        nxt = next((u for u in toks[i + 1:] if not (u.kind == "word" and u.text in CURRENCY_WORDS)), None)
        if t.kind == "op" and t.text == "*" and not (nxt and nxt.kind in ("num", "lp")):
            # a trailing "x"/"×" ("1.5×", "0.68x") is a unit, not an operator
            t = Tok("unit", t.text, t.start, t.end, t.space_before)
        if t.kind == "word":
            w = t.text
            low = w.lower().rstrip(".")
            prev = res[-1] if res else None
            if w in CURRENCY_WORDS:
                continue
            if low in APPROX_WORDS or w == "~":
                approx_next = True
                continue
            if prev is not None and prev.kind == "num" and w in MULTIPLIERS and len(w) > 2:
                n = prev.num
                n.mult_lo = n.mult_hi = MULTIPLIERS[w]
                continue
            if w.startswith("/") and not t.space_before and prev is not None and prev.kind in ("num", "unit"):
                res.append(Tok("unit", w, t.start, t.end, t.space_before))
                continue
            # up to two unit words right after a number ("m3/d", "alert days", "t/yr")
            if prev is not None and low not in STOPWORDS and len(w) <= 15 and (
                    prev.kind == "num" or (prev.kind == "unit" and len(res) > 1 and res[-2].kind == "num")):
                res.append(Tok("unit", w, t.start, t.end, t.space_before))
                continue
        if t.kind == "other" and t.text == "~":
            approx_next = True
            continue
        if t.kind == "num":
            if approx_next:
                t.num.approx = True
            approx_next = False
        res.append(t)
    # "36/84/144" or "Months 36/84": unspaced slashes between integers are lists, not division
    for i, t in enumerate(res):
        if t.kind == "op" and t.text == "/" and not t.space_before and i > 0 and i + 1 < len(res):
            a, b = res[i - 1], res[i + 1]
            if a.kind == "num" and b.kind == "num" and not b.space_before and _plain_int(a) and _plain_int(b):
                t.kind = "word"
    return res


def _plain_int(t: Tok) -> bool:
    n = t.num
    return n.decimals == 0 and n.lo == n.hi and n.mult_lo == 1.0 and not n.pct


# ---------- parsing ----------

class _Parser:
    def __init__(self, toks: list[Tok]):
        self.toks = [t for t in toks if t.kind != "unit"]
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def parse(self):
        node = self.expr()
        if self.peek() is not None:
            raise ValueError("trailing tokens")
        return node

    def expr(self):
        node = self.term()
        while (t := self.peek()) is not None and t.kind == "op" and t.text in "+-":
            self.take()
            node = (t.text, node, self.term())
        return node

    def term(self):
        node = self.power()
        while (t := self.peek()) is not None and t.kind == "op" and t.text in "*/":
            self.take()
            node = (t.text, node, self.power())
        return node

    def power(self):
        node = self.unary()
        t = self.peek()
        if t is not None and t.kind == "op" and t.text == "^":
            self.take()
            node = ("^", node, self.unary())
        return node

    def unary(self):
        t = self.peek()
        if t is not None and t.kind == "op" and t.text == "-":
            self.take()
            return ("neg", self.unary())
        return self.atom()

    def atom(self):
        t = self.take()
        if t is None:
            raise ValueError("unexpected end")
        if t.kind == "num":
            return t.num
        if t.kind == "lp":
            node = self.expr()
            r = self.take()
            if r is None or r.kind != "rp":
                raise ValueError("unbalanced")
            return node
        raise ValueError(f"unexpected {t.text}")


def parse(toks: list[Tok]):
    return _Parser(toks).parse()


def _eval(node, use_mult: bool, end: str, with_err: bool) -> tuple[float, float]:
    """Interval arithmetic over the expression tree."""
    if isinstance(node, Num):
        return node.interval(use_mult, end, with_err)
    if node[0] == "neg":
        lo, hi = _eval(node[1], use_mult, end, with_err)
        return -hi, -lo
    (a, b), (c, d) = _eval(node[1], use_mult, end, with_err), _eval(node[2], use_mult, end, with_err)
    op = node[0]
    if op == "+":
        return a + c, b + d
    if op == "-":
        return a - d, b - c
    if op == "*":
        v = [a * c, a * d, b * c, b * d]
    elif op == "/":
        if c <= 0 <= d:
            raise ZeroDivisionError
        v = [a / c, a / d, b / c, b / d]
    else:
        v = [x ** y for x in (a, b) for y in (c, d)]
    return min(v), max(v)


def _has_range(node) -> bool:
    if isinstance(node, Num):
        return node.lo != node.hi
    return any(_has_range(n) for n in node[1:])


def _pct_nums(node) -> list[Num]:
    if isinstance(node, Num):
        return [node] if node.pct else []
    return [n for sub in node[1:] for n in _pct_nums(sub)]


def _only_products(node) -> bool:
    if isinstance(node, Num):
        return True
    return node[0] in ("*", "/") and all(_only_products(n) for n in node[1:])


Interval = tuple[float, float]
# A candidate reading of an expression: where its low end and its high end may lie (each an interval,
# because the written inputs are rounded). For an expression without ranges both are the same.
Candidate = tuple[Interval, Interval]


def _relative_pct(node):
    """'EUR 70 + 10%' read as a 10% increase: X + p% -> X * (1 + p%), X - p% -> X * (1 - p%).
    Returns None when the expression has no such term."""
    if isinstance(node, Num) or node[0] == "neg":
        return None
    op, left, right = node
    if op in "+-" and isinstance(right, Num) and right.pct and not (isinstance(left, Num) and left.pct):
        return ("*", left, (op, Num(1.0, 1.0, text="1"), right))
    new_left, new_right = _relative_pct(left), _relative_pct(right)
    if new_left is None and new_right is None:
        return None
    return (op, new_left or left, new_right or right)


def computed_candidates(node) -> list[Candidate]:
    out = _candidates(node)
    relative = _relative_pct(node)
    if relative is not None:
        out += _candidates(relative)
    pcts = _pct_nums(node)
    if len(pcts) == 1 and _only_products(node):
        # "20 requests x 60% availability = 8 escalated" reads the complement (40%); accept that reading
        p = pcts[0]
        lo, hi = p.lo, p.hi
        p.lo, p.hi = 100 - hi, 100 - lo
        try:
            out += _candidates(node)
        finally:
            p.lo, p.hi = lo, hi
    return out


def _candidates(node) -> list[Candidate]:
    out = []
    for use_mult in (True, False):
        try:
            lo, hi = _eval(node, use_mult, "lo", True), _eval(node, use_mult, "hi", True)
            if lo[0] + lo[1] > hi[0] + hi[1]:
                lo, hi = hi, lo
            out.append((lo, hi))  # range ends paired (low with low)
            if _has_range(node):
                inner, outer = _eval(node, use_mult, "both", False), _eval(node, use_mult, "both", True)
                out.append(((outer[0], inner[0]), (inner[1], outer[1])))  # full interval arithmetic
        except (ZeroDivisionError, OverflowError, ValueError, TypeError):
            continue
    return out


def _stated_tolerance(n: Num, value: float, scale: float) -> float:
    """How far from the written value the true value may be: half a unit of its last digit."""
    tol = max(_rounding(n, stated=True) * scale, abs(value) * 0.001)
    if n.approx:
        tol = max(tol, abs(value) * 0.05)
    return tol


def _rounding(n: Num, stated: bool = False) -> float:
    """Half a unit of the last written digit. Integer inputs are taken as exact counts ("9 x 45k"), but a
    stated result is rounded ("300M / 7 = 43M"), and "26,000" is a rounded figure either way."""
    if n.decimals:
        return 0.5 * 10.0 ** -n.decimals
    digits = re.sub(r"\D", "", re.split(r"[–—-]", n.text)[0])
    tz = len(digits) - len(digits.rstrip("0"))
    if len(digits) >= 4 and tz:
        return 0.5 * 10.0 ** tz
    return 0.5 if stated else 0.0


# A statement whose result differs by exactly a power of 1000 is a unit shift (MW vs GW, "x 1.0B" dropped
# in a chain), not an arithmetic error.
SCALES = (1.0, 1e3, 1e-3, 1e6, 1e-6, 1e9, 1e-9)


def _overlaps(a: Interval, b: Interval) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def matches(stated: Num, candidates: list[Candidate]) -> bool:
    for use_mult in (True, False):
        for pct_as_fraction in ((True, False) if stated.pct else (False,)):
            def sv(end):
                v = stated.lo if end == "lo" else stated.hi
                m = (stated.mult_lo if end == "lo" else stated.mult_hi) if use_mult else 1.0
                return v * m / (100.0 if pct_as_fraction else 1.0)
            slo, shi = sv("lo"), sv("hi")
            scale = (stated.mult_lo if use_mult else 1.0) / (100.0 if pct_as_fraction else 1.0)
            tlo, thi = _stated_tolerance(stated, slo, scale), _stated_tolerance(stated, shi, scale)
            s_lo, s_hi = (slo - tlo, slo + tlo), (shi - thi, shi + thi)
            for k in SCALES:
                for (a, b), (c, d) in candidates:
                    lo, hi = (a * k, b * k), (c * k, d * k)
                    if _overlaps(s_lo, lo) and _overlaps(s_hi, hi):
                        return True
                    if slo == shi and _overlaps(s_lo, (lo[0], hi[1])) and lo != hi:
                        return True  # one stated value inside a computed range
                    if lo == hi and _overlaps((s_lo[0], s_hi[1]), lo):
                        return True  # one computed value inside a stated range
    return False


def _mid(i: Interval) -> float:
    return (i[0] + i[1]) / 2


def _as_num(c: Candidate) -> Num:
    lo, hi = _mid(c[0]), _mid(c[1])
    return Num(lo, hi, text=_fmt(lo), decimals=6, err=max(c[0][1] - c[0][0], c[1][1] - c[1][0]) / 2)


def _fmt(v: float) -> str:
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "k")):
        if a >= div:
            return f"{v / div:.4g}{suf}"
    return f"{v:.4g}"


def _fmt_range(c: Candidate) -> str:
    lo, hi = _mid(c[0]), _mid(c[1])
    return _fmt(lo) if abs(lo - hi) <= 1e-9 * max(1.0, abs(lo)) else f"{_fmt(lo)}–{_fmt(hi)}"


# ---------- statements ----------

MATH = ("num", "op", "lp", "rp", "unit")


def _longest_suffix_expr(seg: list[Tok]):
    """The longest tail of `seg` that parses as an expression with at least one operator.

    None when the expression is glued to a preceding number ("1.3M (400+300) + 300k": which numbers
    belong to the sum is ambiguous)."""
    j = len(seg)
    while j > 0 and seg[j - 1].kind in MATH:
        j -= 1
    # "USD 50-100 + income USD 30-50 x 3-5": an operator before a label word means the expression goes on
    # to the left, across words; which numbers belong to it is ambiguous
    k = j
    while k > 0 and j - k < 3 and seg[k - 1].kind == "word":
        k -= 1
    if k < j and k > 0 and seg[k - 1].kind == "op":
        return None
    tail = seg[j:]
    while tail and tail[-1].kind == "unit":
        tail = tail[:-1]
    for k in range(len(tail)):
        part = tail[k:]
        if part[0].kind not in ("num", "lp", "op"):
            continue
        if not any(t.kind == "op" for t in part):
            return None
        try:
            node = parse(part)
        except (ValueError, IndexError):
            continue
        before = tail[k - 1] if k > 0 else None
        if before is not None and before.kind in ("num", "unit", "rp"):
            return None
        return node, part
    return None


def _first_number(seg: list[Tok]) -> Tok | None:
    """The stated value at the start of a right-hand side ('= USD 5M', '= Month 42', '= about 1.9B')."""
    words = 0
    for t in seg:
        if t.kind == "num":
            return t
        if t.kind == "word" and words < 2 and t.text.lower() not in STOPWORDS:
            words += 1
            continue
        return None
    return None


def _prefix_expr(seg: list[Tok]):
    """The longest head of `seg` (from its first number) that parses as an expression with an operator."""
    first = _first_number(seg)
    if first is None:
        return None
    i = seg.index(first)
    j = i
    while j < len(seg) and seg[j].kind in MATH:
        j += 1
    run = seg[i:j]
    for k in range(len(run), 0, -1):
        part = run[:k]
        if not any(t.kind == "op" for t in part):
            return None
        try:
            return parse(part), part
        except (ValueError, IndexError):
            continue
    return None


def _clauses(toks: list[Tok]) -> list[list[Tok]]:
    out, cur = [], []
    for t in toks:
        if t.kind == "boundary" or (t.kind == "word" and t.text.lower() in ("and", "or", "but", "vs", "while")):
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        out.append(cur)
    return out


def _text(line: str, part: list[Tok]) -> str:
    return line[part[0].start:part[-1].end] if part else ""


def _numbers(part: list[Tok]) -> set[str]:
    return {t.text for t in part if t.kind == "num"}


def check_line(line: str) -> list[tuple[str, str, str, bool, str]]:
    """(expression, stated, computed, ok, excerpt) for each checkable statement in one line."""
    results = []
    for clause in _clauses(tokenize(line)):
        eq_idx = [i for i, t in enumerate(clause) if t.kind == "eq"]
        if not eq_idx:
            continue
        bounds = [-1] + eq_idx + [len(clause)]
        segs = [clause[bounds[i] + 1:bounds[i + 1]] for i in range(len(bounds) - 1)]
        excerpt = _text(line, clause)
        for i in range(len(segs) - 1):
            left, right = segs[i], segs[i + 1]
            if not right or right[0].kind == "date":
                continue
            stated = _first_number(right)
            if stated is None:
                continue
            si = right.index(stated)
            after = right[si + 1] if si + 1 < len(right) else None
            if after is not None and after.kind == "word" and after.text == "/":
                continue  # "= Years 3/7": a list, not a value
            rexpr = _prefix_expr(right)
            lexpr = _longest_suffix_expr(left)
            if lexpr is not None:
                node, part = lexpr
                if rexpr is not None and _numbers(rexpr[1]) - {stated.text} & _numbers(part):
                    continue  # "50 MLD x 8000 h = 2,083 m3/h x 8000": the same product restated in other units
                cands = computed_candidates(node)
                if not cands:
                    continue
                ok = matches(stated.num, cands)
                if not ok and rexpr is not None:
                    # "a x b = c / d = e": the right side may itself restate the value as an expression
                    rc = computed_candidates(rexpr[0])
                    ok = any(matches(_as_num(c), cands) for c in rc[:1])
                results.append((_text(line, part), stated.text, _fmt_range(cands[0]), ok, excerpt))
            elif i + 1 == len(segs) - 1 and left and left[-1].kind in ("num", "unit") and rexpr is not None:
                # "USD 13.33M/yr = 16.67M m3 x USD 0.80/m3": the value is stated first
                lhs = next((t for t in reversed(left) if t.kind == "num"), None)
                if lhs is None:
                    continue
                node, part = rexpr
                cands = computed_candidates(node)
                if not cands:
                    continue
                results.append((_text(line, part), lhs.text, _fmt_range(cands[0]), matches(lhs.num, cands), excerpt))
    return results


def _strip_markdown(line: str) -> str:
    return re.sub(r"\*\*|__|`", "", line)


def check_text(document: str, text: str) -> list[Finding]:
    findings = []
    for no, raw in enumerate(text.splitlines(), start=1):
        line = _strip_markdown(raw)
        if "=" not in line and "≈" not in line:
            continue
        for expr, stated, computed, ok, excerpt in check_line(line):
            findings.append(Finding(document, no, excerpt.strip()[:240], expr, stated, computed, ok))
    return findings
