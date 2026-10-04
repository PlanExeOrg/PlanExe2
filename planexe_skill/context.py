"""The object a skill's run(ctx) receives."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

from planexe_skill.llm.base import Backend, LLMResult
from planexe_skill.skill import Skill

T = TypeVar("T")
R = TypeVar("R")


DEFAULT_MAX_WORDS_PER_FIELD = 160
FACT_CHECK_INSTRUCTION = (
    "\n\n# Fact checking\nBefore answering, identify the few real-world facts your answer depends on most "
    "(laws and regulations, geography, prices and costs, technology readiness, named organizations or "
    "precedents) that you are not certain about, and verify them with web search (at most 3 searches; "
    "none if you are confident). Do not invent facts, names or numbers; if something could not be verified, "
    "say so briefly in the relevant field.")
# PlanExe's own length hints ("50-70 words", "1-2 sentences", "~30 words", "3-5 items") win.
_LENGTH_HINT = re.compile(r"\b(\d+\s*(-|–|to)\s*\d+|~?\d+|one|two|three)\s+(words?|sentences?)\b|"
                          r"\bone sentence\b|\bone short sentence\b", re.I)


def with_length_budget(schema: dict, max_words: int) -> dict:
    """Copy of `schema` where every free-text string field says 'At most N words.'"""
    import copy
    schema = copy.deepcopy(schema)

    def is_text(node: dict) -> bool:
        if "enum" in node or "const" in node:
            return False
        if node.get("type") == "string":
            return True
        return any(isinstance(a, dict) and a.get("type") == "string" and "enum" not in a
                   for a in node.get("anyOf", []))

    def visit(node):
        if isinstance(node, dict):
            for key, sub in list(node.get("properties", {}).items()):
                if isinstance(sub, dict) and is_text(sub) and not _LENGTH_HINT.search(sub.get("description", "")):
                    desc = sub.get("description", "").rstrip()
                    sub["description"] = (desc + " " if desc else "") + f"At most {max_words} words."
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)
    visit(schema)
    return schema


class SkillContractError(Exception):
    """A skill read or wrote a file it did not declare in SKILL.md."""


class SkillContext:
    def __init__(self, run_dir: Path, staging_dir: Path, skill: Skill, backend: Backend,
                 llm_slots: threading.Semaphore, on_llm_call: Callable[[str, dict], None] | None = None,
                 log_path: Path | None = None, cache_dir: Path | None = None):
        self.run_dir = run_dir
        self.staging_dir = staging_dir
        self.skill = skill
        self.skill_dir = skill.dir
        self.backend = backend
        self._llm_slots = llm_slots
        self._on_llm_call = on_llm_call
        self._log_path = log_path
        self._log_lock = threading.Lock()
        self.llm_calls = 0
        self.cache_hits = 0
        # Resume points: every completed call is stored here. When a stage fails halfway (e.g. at
        # question 15 of 16) the re-run replays the finished calls instantly. The runner deletes
        # the cache once the stage succeeds, so a later --force gets fresh answers.
        self.cache_dir = cache_dir

    # ---------- files ----------
    def _check_read(self, name: str) -> None:
        if name in self.skill.inputs or self.skill.produces(name):
            return
        raise SkillContractError(
            f"skill '{self.skill.name}' tried to read '{name}', which is not listed in its SKILL.md inputs. "
            f"Add it to `inputs:` so the DAG knows about the dependency.")

    def _check_write(self, name: str) -> None:
        if self.skill.produces(name):
            return
        raise SkillContractError(
            f"skill '{self.skill.name}' tried to write '{name}', which is not listed in its SKILL.md outputs.")

    def _resolve(self, name: str) -> Path:
        staged = self.staging_dir / name
        return staged if staged.exists() else self.run_dir / name

    def path(self, name: str) -> Path:
        """Filesystem path of a declared input (or an output already written by this skill)."""
        self._check_read(name)
        return self._resolve(name)

    def exists(self, name: str) -> bool:
        self._check_read(name)
        return self._resolve(name).exists()

    def read_text(self, name: str) -> str:
        self._check_read(name)
        p = self._resolve(name)
        if not p.exists():
            raise FileNotFoundError(f"skill '{self.skill.name}': input file '{name}' does not exist in {self.run_dir}")
        return p.read_text(encoding="utf-8")

    def read_json(self, name: str) -> Any:
        return json.loads(self.read_text(name))

    def write_text(self, name: str, text: str) -> None:
        self._check_write(name)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        (self.staging_dir / name).write_text(text, encoding="utf-8")

    def write_json(self, name: str, obj: Any, indent: int = 2) -> None:
        self.write_text(name, json.dumps(obj, indent=indent, ensure_ascii=False))

    def skill_file(self, rel: str) -> str:
        """Read a text file shipped inside the skill folder (prompts, templates)."""
        return (self.skill.dir / rel).read_text(encoding="utf-8")

    def skill_json(self, rel: str) -> Any:
        return json.loads(self.skill_file(rel))

    # ---------- logging ----------
    def log(self, msg: str) -> None:
        if self._log_path is None:
            return
        with self._log_lock:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

    # ---------- llm ----------
    def llm(self, system: str, user: str, schema: dict | None = None, tier: str | None = None,
            label: str = "") -> LLMResult:
        """One LLM call. Concurrency across the whole run is bounded by the runner."""
        tier = tier or self.skill.tier
        model = self.backend.model_for(tier)
        # The reasoning tier fact-checks with web search (skills can opt out with `fact_check: false`),
        # so the foundational stages hand verified facts to the many single-shot stages downstream.
        web_search = bool(self.skill.meta.get("fact_check", tier == "high")) and tier == "high"
        if web_search:
            system = system.rstrip() + FACT_CHECK_INSTRUCTION
        # Length budget for the non-reasoning tiers: without it Haiku writes essays per field,
        # which makes calls take minutes. Skills can tune it via `max_words_per_field:` (0 = off).
        budget = int(self.skill.meta.get("max_words_per_field", DEFAULT_MAX_WORDS_PER_FIELD) or 0)
        if tier != "high" and budget > 0 and schema is not None:
            schema = with_length_budget(schema, budget)
            system = (system.rstrip() + f"\n\nBe concise: keep every text field to at most {budget} words; "
                      "prefer short, specific sentences over essays.")
        cache_file = None
        if self.cache_dir is not None:
            key = hashlib.sha256(json.dumps([model, system, user, schema, web_search], sort_keys=True).encode()).hexdigest()[:24]
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                try:
                    c = json.loads(cache_file.read_text(encoding="utf-8"))
                    self.cache_hits += 1
                    self.llm_calls += 1
                    self.log(f"LLM call {label} replayed from resume cache ({cache_file.name})")
                    return LLMResult(data=c["data"], text=c["text"], metadata={**c["metadata"], "cached": True})
                except (OSError, json.JSONDecodeError, KeyError):
                    pass
        self.log(f"LLM call {label} tier={tier} model={self.backend.model_for(tier)}\n"
                 f"--- system ---\n{system}\n--- user ---\n{user}\n--- schema ---\n"
                 f"{json.dumps(schema)[:3000] if schema else None}")
        with self._llm_slots:
            start = time.time()
            result: LLMResult | None = None
            try:
                result = self.backend.complete(system, user, schema, tier, web_search=web_search)
            finally:
                if self._on_llm_call:
                    self._on_llm_call(self.skill.name, {"tier": tier, "success": result is not None,
                                                        "duration_seconds": time.time() - start,
                                                        "metadata": result.metadata if result else {}})
        assert result is not None
        self.llm_calls += 1
        if cache_file is not None:
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache_file.with_suffix(".tmp")
                tmp.write_text(json.dumps({"data": result.data, "text": result.text, "metadata": result.metadata}),
                               encoding="utf-8")
                tmp.replace(cache_file)
            except (OSError, TypeError):
                pass
        self.log(f"--- response ({result.metadata.get('duration_seconds')}s) ---\n{result.text[:20000]}")
        return result

    def map(self, fn: Callable[[T], R], items: Iterable[T], max_workers: int = 8) -> list[R]:
        """Run fn over items in threads (results in input order). LLM concurrency stays bounded."""
        items = list(items)
        if len(items) <= 1:
            return [fn(i) for i in items]
        with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as ex:
            return list(ex.map(fn, items))
