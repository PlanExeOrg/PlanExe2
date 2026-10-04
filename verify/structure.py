"""Structural comparison of JSON and markdown outputs."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Keys whose *contents* depend on the model/backend; only their presence is compared.
OPAQUE_KEYS = {"metadata", "system_prompt", "user_prompt", "llm_classname"}


def _type_name(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def shape(v: Any) -> Any:
    """Canonical shape: dict -> {key: shape}, list -> [merged item shape], scalar -> type name."""
    if isinstance(v, dict):
        return {k: ("<opaque>" if k in OPAQUE_KEYS else shape(x)) for k, x in v.items()}
    if isinstance(v, list):
        merged: Any = None
        for item in v:
            merged = _merge(merged, shape(item))
        return [merged] if merged is not None else []
    return _type_name(v)


def _merge(a: Any, b: Any) -> Any:
    if a is None:
        return b
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _merge(out.get(k), v)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if not a:
            return b
        if not b:
            return a
        return [_merge(a[0], b[0])]
    if a == b:
        return a
    if "null" in (a, b):
        return b if a == "null" else a
    return f"{a}|{b}" if isinstance(a, str) and isinstance(b, str) else a


def diff_shapes(expected: Any, actual: Any, path: str = "$") -> list[str]:
    problems: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {actual!r:.40}"]
        for k in expected:
            if k not in actual:
                problems.append(f"{path}.{k}: missing key")
            else:
                problems += diff_shapes(expected[k], actual[k], f"{path}.{k}")
        for k in actual:
            if k not in expected:
                problems.append(f"{path}.{k}: extra key")
        return problems
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected list, got {actual!r:.40}"]
        if expected and actual:
            problems += diff_shapes(expected[0], actual[0], f"{path}[]")
        return problems
    if expected == "<opaque>" or actual == "<opaque>":
        return []
    if isinstance(expected, str) and isinstance(actual, str):
        exp = set(expected.split("|"))
        act = set(actual.split("|"))
        if "null" in exp or "null" in act or exp & act:
            return []
        return [f"{path}: type {actual} != expected {expected}"]
    return [f"{path}: shape mismatch"]


def compare_json_files(baseline: Path, candidate: Path) -> list[str]:
    try:
        b = json.loads(baseline.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []  # baseline itself is not JSON; nothing to compare
    try:
        c = json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"candidate is not valid JSON: {e}"]
    return diff_shapes(shape(b), shape(c))


HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def headings(md: str) -> list[tuple[int, str]]:
    out = []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = HEADING.match(line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip()))
    return out


def template_headings(baseline_texts: list[str]) -> list[tuple[int, str]]:
    """Headings present in every baseline: these come from the template, not the content."""
    if not baseline_texts:
        return []
    sets = [set(headings(t)) for t in baseline_texts]
    common = set.intersection(*sets)
    return [h for h in headings(baseline_texts[0]) if h in common]


def compare_markdown(template: list[tuple[int, str]], candidate_text: str) -> list[str]:
    got = set(headings(candidate_text))
    return [f"missing heading {'#' * lvl} {txt}" for lvl, txt in template if (lvl, txt) not in got]
