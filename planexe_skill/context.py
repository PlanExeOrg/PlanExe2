"""The object a skill's run(ctx) receives."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

from planexe_skill.llm.base import Backend, LLMResult
from planexe_skill.skill import Skill

T = TypeVar("T")
R = TypeVar("R")


class SkillContractError(Exception):
    """A skill read or wrote a file it did not declare in SKILL.md."""


class SkillContext:
    def __init__(self, run_dir: Path, staging_dir: Path, skill: Skill, backend: Backend,
                 llm_slots: threading.Semaphore, on_llm_call: Callable[[str, dict], None] | None = None,
                 log_path: Path | None = None):
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

    def path(self, name: str) -> Path:
        staged = self.staging_dir / name
        return staged if staged.exists() else self.run_dir / name

    def exists(self, name: str) -> bool:
        self._check_read(name)
        return self.path(name).exists()

    def read_text(self, name: str) -> str:
        self._check_read(name)
        p = self.path(name)
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
        self.log(f"LLM call {label} tier={tier} model={self.backend.model_for(tier)}\n"
                 f"--- system ---\n{system}\n--- user ---\n{user}\n--- schema ---\n"
                 f"{json.dumps(schema)[:3000] if schema else None}")
        with self._llm_slots:
            start = time.time()
            result: LLMResult | None = None
            try:
                result = self.backend.complete(system, user, schema, tier)
            finally:
                if self._on_llm_call:
                    self._on_llm_call(self.skill.name, {"tier": tier, "success": result is not None,
                                                        "duration_seconds": time.time() - start,
                                                        "metadata": result.metadata if result else {}})
        assert result is not None
        self.llm_calls += 1
        self.log(f"--- response ({result.metadata.get('duration_seconds')}s) ---\n{result.text[:20000]}")
        return result

    def map(self, fn: Callable[[T], R], items: Iterable[T], max_workers: int = 8) -> list[R]:
        """Run fn over items in threads (results in input order). LLM concurrency stays bounded."""
        items = list(items)
        if len(items) <= 1:
            return [fn(i) for i in items]
        with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as ex:
            return list(ex.map(fn, items))
