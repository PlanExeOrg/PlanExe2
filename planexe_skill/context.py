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


_COUNT_HINT = re.compile(r"\b(\d+\s*(-|–|to)\s*\d+|exactly \d+|at least \d+|at most \d+|\d+\s+items?)\b", re.I)


def with_length_budget(schema: dict, max_words: int, max_items: int = 0) -> dict:
    """Copy of `schema` where every free-text string field says 'At most N words.' and, when
    max_items > 0, every list without its own count hint says 'At most N items.'"""
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
                if (max_items > 0 and isinstance(sub, dict) and sub.get("type") == "array"
                        and not _COUNT_HINT.search(sub.get("description", ""))):
                    desc = sub.get("description", "").rstrip()
                    sub["description"] = (desc + " " if desc else "") + f"At most {max_items} items."
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)
    visit(schema)
    return schema


EPISTEMIC_INSTRUCTION = (
    "\n\n# Numbers and provenance\nDo not present invented numbers as facts. For any figure that is not a "
    "user constraint or an externally established benchmark, mark what it is, e.g. \"(proposed threshold)\" or "
    "\"(estimate)\"; mark user-given figures \"(user constraint)\" only when that helps. Never turn an example "
    "value from the input documents (\"e.g. ...\") into a requirement.")


def project_start(run_dir: Path):
    from datetime import date
    try:
        utc = json.loads((run_dir / "start_time.json").read_text(encoding="utf-8")).get("server_iso_utc", "")
        return date.fromisoformat(utc[:10])
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def calendar_reference(run_dir: Path) -> str:
    """'Month N = date' table from the run's start date, so milestone dates are computed, not guessed."""
    p = run_dir / "start_time.json"
    try:
        utc = json.loads(p.read_text(encoding="utf-8")).get("server_iso_utc", "")
        y, m, d = (int(x) for x in utc[:10].split("-"))
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    rows = []
    for n in list(range(0, 13, 1)) + list(range(15, 121, 3)):
        yy, mm = y + (m - 1 + n) // 12, (m - 1 + n) % 12 + 1
        rows.append(f"Month {n} = {yy:04d}-{mm:02d}-{min(d, 28 if mm == 2 else 30 if mm in (4, 6, 9, 11) else 31):02d}")
    return (f"\n\n# Time references\nIn this plan, today is {y:04d}-{m:02d}-{d:02d} (Month 0, the project start). Ignore any "
            "other notion of the current date. Refer to points in time as month offsets from the project start: "
            "\"Month 3\", \"Month 3.5\", \"Months 48-72\". Do not write calendar dates yourself; they are added "
            "automatically. For orientation only (Month N = start date + N months):\n" + "; ".join(rows))


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
        self._calendar = calendar_reference(run_dir)
        self._start = project_start(run_dir)
        self.project_start = self._start  # date of Month 0, or None

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

    def _canonical_facts_block(self) -> str:
        try:
            facts = json.loads(self._resolve("canonical_facts.json").read_text(encoding="utf-8")).get("facts") or []
        except (OSError, json.JSONDecodeError):
            return ""
        lines = [f"- {f.get('key')}: {f.get('value')} ({str(f.get('kind', '')).replace('_', ' ')})" for f in facts]
        return ("\n\n# Canonical facts\nThese values were reconciled for this plan. Whenever you mention one of these "
                "quantities, use exactly this value; do not introduce a different number for it. If an input document "
                "states a different value, the canonical fact wins: do not repeat the document's value. In particular, the "
                "assumptions documents were written before these facts and are superseded wherever they differ. "
                "Label any other figure "
                "you need as (estimate) or (proposed threshold).\n" + "\n".join(lines))

    def run_provenance(self) -> dict:
        """RUN_DIR/planexe_provenance.json as maintained by the runner (not a declared input: it describes
        how the run was produced, like the run's start date)."""
        from planexe_skill.provenance import PROVENANCE_FILENAME
        try:
            return json.loads((self.run_dir / PROVENANCE_FILENAME).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    # ---------- llm ----------
    def llm(self, system: str, user: str, schema: dict | None = None, tier: str | None = None,
            label: str = "") -> LLMResult:
        """One LLM call. Concurrency across the whole run is bounded by the runner."""
        tier = tier or self.skill.tier
        model = self.backend.model_for(tier)
        # The reasoning tier fact-checks with web search (skills can opt out with `fact_check: false`),
        # so the foundational stages hand verified facts to the many single-shot stages downstream.
        fact_check = self.skill.meta.get("fact_check", tier == "high")
        web_search = bool(fact_check) and tier == "high"
        if web_search:
            system = system.rstrip() + FACT_CHECK_INSTRUCTION
            if fact_check == "required":
                system += (" For this task, searching is required: run 1-2 web searches to verify the real-world "
                           "precedents, organizations and figures you cite before answering.")
        # Canonical facts (see skills/canonical_facts): stages that declare the file must use these values.
        # They go at the end of the user message: models without reasoning ignore them at the end of a long
        # system prompt (measured on the datacenter run).
        facts_block = ""
        if "canonical_facts.json" in self.skill.inputs and self._resolve("canonical_facts.json").exists():
            facts_block = self._canonical_facts_block()
        # Applies to every LLM call: month->date table in the system prompt; the provenance rule goes
        # at the end of the user message, where models without reasoning reliably notice it.
        system = system.rstrip() + self._calendar
        user = user.rstrip() + facts_block + EPISTEMIC_INSTRUCTION
        # Length budget for the non-reasoning tiers: without it Haiku writes essays per field,
        # which makes calls take minutes. Skills can tune it via `max_words_per_field:` (0 = off).
        budget = int(self.skill.meta.get("max_words_per_field", DEFAULT_MAX_WORDS_PER_FIELD) or 0)
        max_items = int(self.skill.meta.get("max_items_per_list", 0) or 0)
        if tier != "high" and budget > 0 and schema is not None:
            schema = with_length_budget(schema, budget, max_items)
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
        if self._start is not None and self.skill.meta.get("calendar_fix", True) is not False:
            # Calendar dates next to "Month N" are derived, not guessed: recompute them.
            from planexe_skill.calendar_fix import fix_text, fix_value
            data, n1 = fix_value(result.data, self._start)
            text, n2 = fix_text(result.text or "", self._start)
            if n1 or n2:
                self.log(f"calendar fix: corrected {max(n1, n2)} month/date pair(s)")
                result = LLMResult(data=data, text=text, metadata={**result.metadata, "calendar_fixes": max(n1, n2)})
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
