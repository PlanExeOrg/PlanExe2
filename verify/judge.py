"""Blind pairwise LLM judge: is the new output on par with / better than the baseline?"""
from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from planexe_skill.llm.claude_cli import ClaudeCLIBackend
from verify.structure import OPAQUE_KEYS

JUDGE_MODEL = "claude-sonnet-5-5"
MAX_CHARS = 150_000

SYSTEM = """You are a strict, impartial reviewer of intermediary documents produced by an automated
project-planning pipeline. Each pipeline stage turns a user's plan prompt (plus earlier stage outputs)
into a document that later stages build on.

You get the user's plan prompt, what the stage is supposed to do, and two candidate outputs, A and B,
for the same stage. Decide which candidate better fulfills the stage's purpose for THIS plan.

Judge on:
1. Faithfulness: respects the plan prompt's facts, constraints, location, budget, scale; no invented
   contradictions, no generic boilerplate that ignores the prompt.
2. Specificity and insight: concrete, plan-specific, decision-useful content; catches real risks/issues.
3. Correctness and internal consistency: numbers, logic, classifications make sense.
4. Fitness for the format: follows the stage's expected structure, complete (no truncation, no empty
   or placeholder sections).
5. Usefulness for downstream planning stages.

Do not prefer an answer just because it is longer or more verbose. Ignore superficial formatting
differences (whitespace, ordering of JSON keys). If both are about equally good, answer "tie".
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {"type": "string", "description": "Brief comparison of A and B on the criteria."},
        "score_a": {"type": "integer", "minimum": 1, "maximum": 10},
        "score_b": {"type": "integer", "minimum": 1, "maximum": 10},
        "winner": {"type": "string", "enum": ["A", "B", "tie"]},
    },
    "required": ["analysis", "score_a", "score_b", "winner"],
    "additionalProperties": False,
}


def _strip_opaque(v):
    if isinstance(v, dict):
        return {k: _strip_opaque(x) for k, x in v.items() if k not in OPAQUE_KEYS}
    if isinstance(v, list):
        return [_strip_opaque(x) for x in v]
    return v


def load_for_judging(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".json":
        try:
            text = json.dumps(_strip_opaque(json.loads(text)), indent=1, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n...[truncated for judging]"
    return text


def _user_prompt(plan: str, stage_desc: str, filename: str, a: str, b: str) -> str:
    return (f"# Plan prompt\n{plan}\n\n# Stage\n{stage_desc}\n\n# File\n{filename}\n\n"
            f"# Candidate A\n<<<A\n{a}\nA>>>\n\n# Candidate B\n<<<B\n{b}\nB>>>\n")


def judge_pair(plan: str, stage_desc: str, filename: str, baseline_text: str, new_text: str,
               backend: ClaudeCLIBackend | None = None, seed: int | None = None) -> dict:
    """Two blind runs with swapped positions. Returns winner in {'new','baseline','tie'}."""
    backend = backend or ClaudeCLIBackend(models={"high": JUDGE_MODEL}, efforts={"high": "high"})
    rnd = random.Random(seed)
    first_new_is_a = rnd.random() < 0.5
    orders = [first_new_is_a, not first_new_is_a]

    def one(new_is_a: bool) -> dict:
        a, b = (new_text, baseline_text) if new_is_a else (baseline_text, new_text)
        r = backend.complete(SYSTEM, _user_prompt(plan, stage_desc, filename, a, b), SCHEMA, "high")
        d = r.data
        w = d["winner"]
        winner = "tie" if w == "tie" else ("new" if (w == "A") == new_is_a else "baseline")
        score_new = d["score_a"] if new_is_a else d["score_b"]
        score_base = d["score_b"] if new_is_a else d["score_a"]
        return {"winner": winner, "score_new": score_new, "score_baseline": score_base,
                "analysis": d["analysis"]}

    with ThreadPoolExecutor(max_workers=2) as ex:
        runs = list(ex.map(one, orders))
    w = {r["winner"] for r in runs}
    if len(w) == 1:
        verdict = runs[0]["winner"]
    elif w == {"new", "tie"}:
        verdict = "new"
    elif w == {"baseline", "tie"}:
        verdict = "baseline"
    else:
        verdict = "tie"  # position-dependent disagreement
    return {"verdict": verdict,
            "score_new": sum(r["score_new"] for r in runs) / 2,
            "score_baseline": sum(r["score_baseline"] for r in runs) / 2,
            "runs": runs}
