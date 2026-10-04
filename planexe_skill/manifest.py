"""Content-hash manifest that decides which stages are dirty.

A stage must (re)run when:
  * one of its outputs is missing,
  * its skill folder changed since it last ran,
  * one of its input files changed since it last ran.

Hand-edited outputs do NOT make the stage itself dirty (the edit is kept), but
downstream stages see a changed input and re-run.

Outputs that exist without a manifest record are "adopted" as clean, so a run
dir can be seeded from an existing PlanExe run and individual stages re-run.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from planexe_skill.skill import Skill

MANIFEST_DIRNAME = ".planexe_skill"
MANIFEST_FILENAME = "manifest.json"


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def hash_file(path: Path) -> str:
    return hash_bytes(path.read_bytes())


def hash_dir(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if "__pycache__" in p.parts or not p.is_file() or p.name == ".DS_Store":
            continue
        h.update(str(p.relative_to(path)).encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


def existing_outputs(skill: Skill, run_dir: Path) -> list[str]:
    """Output files of `skill` currently present in run_dir (fan-out patterns expanded)."""
    found = [o for o in skill.fixed_outputs() if (run_dir / o).exists()]
    for pattern in skill.pattern_outputs():
        rx = Skill.pattern_regex(pattern)
        matches = [p.name for p in run_dir.iterdir() if rx.match(p.name)]
        found.extend(sorted(matches, key=lambda n: int(rx.match(n).group(1))))
    return found


@dataclass
class StageStatus:
    dirty: bool
    reasons: list[str] = field(default_factory=list)
    adoptable: bool = False
    edited_outputs: list[str] = field(default_factory=list)


class Manifest:
    def __init__(self, run_dir: Path, data: dict):
        self.run_dir = run_dir
        self.data = data
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self.run_dir / MANIFEST_DIRNAME / MANIFEST_FILENAME

    @classmethod
    def load(cls, run_dir: Path) -> "Manifest":
        p = run_dir / MANIFEST_DIRNAME / MANIFEST_FILENAME
        data = json.loads(p.read_text()) if p.exists() else {"version": 1, "stages": {}}
        return cls(run_dir, data)

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(self.data, f, indent=2, sort_keys=True)
            os.replace(tmp, self.path)

    def entry(self, name: str) -> dict | None:
        return self.data["stages"].get(name)

    def forget(self, name: str) -> None:
        with self._lock:
            self.data["stages"].pop(name, None)

    def _input_hashes(self, skill: Skill, run_dir: Path) -> dict[str, str | None]:
        return {i: (hash_file(run_dir / i) if (run_dir / i).exists() else None) for i in skill.inputs}

    def record_completed(self, skill: Skill, run_dir: Path, adopted: bool = False) -> None:
        entry = {
            "skill_hash": hash_dir(skill.dir),
            "inputs": self._input_hashes(skill, run_dir),
            "outputs": {o: hash_file(run_dir / o) for o in existing_outputs(skill, run_dir)},
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "adopted": adopted,
        }
        with self._lock:
            self.data["stages"][skill.name] = entry

    def status(self, skill: Skill, run_dir: Path) -> StageStatus:
        missing = [o for o in skill.fixed_outputs() if not (run_dir / o).exists()]
        if missing:
            return StageStatus(True, [f"missing output {m}" for m in missing])
        entry = self.entry(skill.name)
        if entry is None:
            return StageStatus(False, ["outputs exist but were not produced by this runner (adopting)"],
                               adoptable=True)
        gone = [o for o in entry["outputs"] if not (run_dir / o).exists()]
        if gone:
            return StageStatus(True, [f"missing output {g}" for g in gone])
        reasons = []
        if entry["skill_hash"] != hash_dir(skill.dir):
            reasons.append("skill definition changed")
        current = self._input_hashes(skill, run_dir)
        for name, h in current.items():
            if entry["inputs"].get(name) != h:
                reasons.append(f"input changed: {name}")
        edited = [o for o, h in entry["outputs"].items()
                  if (run_dir / o).exists() and hash_file(run_dir / o) != h]
        return StageStatus(bool(reasons), reasons, edited_outputs=edited)
