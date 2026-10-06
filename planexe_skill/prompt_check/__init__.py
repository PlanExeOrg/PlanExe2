"""Pre-flight check of a plan prompt (one LLM call), used before launching the full DAG.

    python3 -m planexe_skill check-prompt --prompt-file my_prompt.txt [--json]
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
ICON = {"present": "✓", "partial": "~", "missing": "✗"}


def check_prompt(prompt: str, backend) -> dict:
    system = (HERE / "system.md").read_text(encoding="utf-8").strip()
    schema = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
    words = len(prompt.split())
    user = f"## Prompt statistics\nWord count: {words}\n\n## Prompt\n{prompt}"
    result = backend.complete(system, user, schema, tier="mid")
    data = dict(result.data or {})
    data["word_count"] = words
    return data


def format_result(r: dict) -> str:
    lines = [f"Verdict: {r.get('verdict')} — {r.get('verdict_reason', '')}",
             f"Words: {r.get('word_count')} (300-800 works best)", "", "Completeness:"]
    for d in r.get("dimensions") or []:
        lines.append(f"  {ICON.get(d['status'], '?')} {d['name']:<16} {d['note']}")
    lines += ["", "Ready to launch: " + ("YES" if r.get("ready") else "NO, refine first")]
    qs = r.get("questions") or []
    if qs:
        lines += ["", "Questions that would most improve the plan:"]
        for i, q in enumerate(qs, start=1):
            lines.append(f"  {i}. {q['question']}")
            if q.get("suggestions"):
                lines.append("     e.g. " + " | ".join(q["suggestions"]))
    return "\n".join(lines)
