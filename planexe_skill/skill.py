"""Load skill folders: skills/<name>/SKILL.md (+ run.py)."""
from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

FAN_OUT_TOKEN = "{n}"


def _scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value in ("true", "false"):
        return value == "true"
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse a tiny YAML subset: `key: scalar`, `key: [a, b]`, and block lists of scalars."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md must start with a '---' frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("SKILL.md frontmatter is not closed with '---'") from None
    meta: dict[str, Any] = {}
    current_list: list | None = None
    for lineno, raw in enumerate(lines[1:end], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = raw.strip()
        if stripped.startswith("- ") and current_list is not None:
            current_list.append(_scalar(stripped[2:]))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if not m:
            raise ValueError(f"SKILL.md frontmatter line {lineno} not understood: {raw!r}")
        key, value = m.group(1), m.group(2).strip()
        current_list = None
        if value == "":
            current_list = []
            meta[key] = current_list
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            meta[key] = [_scalar(v) for v in inner.split(",")] if inner else []
        else:
            meta[key] = _scalar(value)
    return meta, "\n".join(lines[end + 1:])


@dataclass
class Skill:
    name: str
    description: str
    inputs: list[str]
    outputs: list[str]
    tier: str
    est_llm_calls: int
    dir: Path
    body: str = ""
    uses: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    _module: ModuleType | None = field(default=None, repr=False)

    def fixed_outputs(self) -> list[str]:
        return [o for o in self.outputs if FAN_OUT_TOKEN not in o]

    def pattern_outputs(self) -> list[str]:
        return [o for o in self.outputs if FAN_OUT_TOKEN in o]

    @staticmethod
    def pattern_regex(pattern: str) -> re.Pattern:
        head, tail = pattern.split(FAN_OUT_TOKEN, 1)
        return re.compile("^" + re.escape(head) + r"(\d+)" + re.escape(tail) + "$")

    def produces(self, filename: str) -> bool:
        if filename in self.fixed_outputs():
            return True
        return any(self.pattern_regex(p).match(filename) for p in self.pattern_outputs())

    def module(self) -> ModuleType:
        if self._module is None:
            path = self.dir / "run.py"
            if not path.exists():
                raise FileNotFoundError(f"skill '{self.name}' has no run.py at {path}")
            spec = importlib.util.spec_from_file_location(f"planexe_skills.{self.name}", path)
            assert spec is not None and spec.loader is not None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if not hasattr(mod, "run"):
                raise AttributeError(f"{path} must define run(ctx)")
            self._module = mod
        return self._module


def load_skill(skill_dir: Path) -> Skill:
    path = skill_dir / "SKILL.md"
    try:
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"{path}: {e}") from None
    name = meta.get("name", skill_dir.name)
    if name != skill_dir.name:
        raise ValueError(f"{path}: name '{name}' must match folder name '{skill_dir.name}'")
    return Skill(
        name=name,
        description=str(meta.get("description", "")),
        inputs=list(meta.get("inputs", [])),
        outputs=list(meta.get("outputs", [])),
        tier=str(meta.get("tier", "low")),
        est_llm_calls=int(meta.get("est_llm_calls", 0)),
        dir=skill_dir,
        body=body,
        uses=list(meta.get("uses", [])),
        meta=meta,
    )


def load_skills(root: Path) -> dict[str, Skill]:
    skills = {}
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            s = load_skill(d)
            skills[s.name] = s
    return skills
