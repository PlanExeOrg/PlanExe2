"""Minimal JSON-schema validation (the subset pydantic emits): type, properties, required, items,
enum, $ref/$defs, anyOf. Returns a list of human-readable problems (empty = valid)."""
from __future__ import annotations

import json
import re
from typing import Any

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


def _type_ok(value: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    py = _TYPES.get(t)
    return True if py is None else isinstance(value, py)


def validate(value: Any, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    root = root or schema
    if "$ref" in schema:
        ref = schema["$ref"]
        m = re.match(r"^#/\$defs/(.+)$", ref)
        if not m or m.group(1) not in root.get("$defs", {}):
            return []
        return validate(value, root["$defs"][m.group(1)], root, path)
    if "anyOf" in schema:
        for sub in schema["anyOf"]:
            if not validate(value, sub, root, path):
                return []
        return [f"{path}: does not match any allowed shape"]
    problems: list[str] = []
    t = schema.get("type")
    if isinstance(t, list):
        if not any(_type_ok(value, x) for x in t):
            return [f"{path}: expected one of {t}"]
    elif isinstance(t, str) and not _type_ok(value, t):
        return [f"{path}: expected {t}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                problems.append(f"{path}.{key}: missing required key")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                problems += validate(value[key], sub, root, f"{path}.{key}")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(value):
            problems += validate(item, schema["items"], root, f"{path}[{i}]")
    return problems


def extract_json_object(text: str) -> Any:
    """Parse the first JSON object in a model reply (tolerates ```json fences and surrounding prose)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in the reply")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj
