"""Which code produced which part of a plan.

A run can mix code versions: stages are re-generated when inputs or skills change, runs are resumed,
intermediary files are hand-edited and their downstream re-generated, and a whole plan can be
re-generated later from the same prompt. So this is recorded per stage (in the manifest) and
summarized in the run dir as `planexe_report_metadata.json`, which the report renders as its "Report
Metadata" section. (Called planexe_provenance.json until 2026-10-07; `write` removes that old file.)

Plan dates are separate from generation dates: the plan's start date (Month 0, `start_time.json`)
may be in the past or the future relative to when it is generated.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from functools import lru_cache
from pathlib import Path

from planexe_skill import REPO_ROOT

GENERATOR_NAME = "PlanExe2"
METADATA_FILENAME = "planexe_report_metadata.json"
LEGACY_FILENAME = "planexe_provenance.json"


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _repo_from_remote(url: str | None) -> str | None:
    """'git@github.com:PlanExeOrg/PlanExe2.git' / 'https://github.com/PlanExeOrg/PlanExe2' -> 'PlanExeOrg/PlanExe2'."""
    if not url:
        return None
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else url


@lru_cache(maxsize=1)
def generator_info() -> dict:
    """Name, version, repo, commit and git tag of the code running now (cached per process)."""
    commit = _git("rev-parse", "HEAD")
    if commit is None:  # not a git checkout (e.g. a downloaded archive)
        return {"name": GENERATOR_NAME, "version": "unknown", "repo": None, "commit": None, "commit_short": None,
                "tag": None, "describe": None, "dirty": None, "commit_date": None}
    tag = _git("describe", "--tags", "--exact-match", "HEAD")
    dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))
    commit_date = _git("show", "-s", "--format=%cd", "--date=short", "HEAD")
    short = commit[:7]
    # `git describe`: "v2.0.0" on the tag, "v2.0.0-3-gabc1234" three commits later, the short commit if
    # there is no tag yet; "+modified" when the working tree has uncommitted changes.
    version = _git("describe", "--tags", "--always") or short
    if dirty:
        version += "+modified"
    return {
        "name": GENERATOR_NAME,
        "version": version,
        "repo": _repo_from_remote(_git("remote", "get-url", "origin")),
        "commit": commit,
        "commit_short": short,
        "tag": tag,
        "describe": _git("describe", "--tags", "--always", "--dirty"),
        "dirty": dirty,
        "commit_date": commit_date,
    }


def generator_brief() -> dict:
    """Compact form embedded in raw JSON metadata and per-stage manifest entries."""
    g = generator_info()
    return {k: g[k] for k in ("name", "version", "repo", "commit", "tag", "dirty")}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _searches_from_usage(run_dir: Path) -> dict[str, int]:
    """Web searches per stage from usage_metrics.jsonl (runs recorded before the manifest kept the count)."""
    out: dict[str, int] = {}
    try:
        lines = (run_dir / "usage_metrics.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("success") and row.get("web_searches"):
            out[row["stage"]] = out.get(row["stage"], 0) + int(row["web_searches"])
    return out


def build(run_dir: Path, dag, manifest) -> dict:
    """Summarize the manifest (per stage: generator, models, calls, searches) plus the run's plan dates."""
    stages = {}
    usage_searches = None
    hand_edited = []
    for name in dag.order():
        entry = manifest.entry(name)
        if entry is None:
            continue
        stages[name] = {
            "generated_at": entry.get("completed_at"),
            "adopted": entry.get("adopted", False),
            "generator": entry.get("generator"),
            "models": entry.get("models", []),
            "llm_calls": entry.get("llm_calls", 0),
        }
        if "web_searches" in entry:
            stages[name]["web_searches"] = entry["web_searches"]
        elif entry.get("llm_calls"):
            if usage_searches is None:
                usage_searches = _searches_from_usage(run_dir)
            stages[name]["web_searches"] = usage_searches.get(name, 0)
        st = manifest.status(dag.skills[name], run_dir)
        hand_edited += [{"stage": name, "file": f} for f in st.edited_outputs]
    versions = sorted({(s["generator"] or {}).get("version", "unknown") for s in stages.values()
                       if not s["adopted"]})
    start = _read_json(run_dir / "start_time.json").get("server_iso_utc", "")[:10] or None
    meta = _read_json(run_dir / "planexe_metadata.json")
    return {
        "generator": generator_info(),
        "plan_start_date": start,
        "plan_date_in_prompt": _read_json(run_dir / "plan_raw.json").get("pretty_date"),
        "created_at": meta.get("created_at"),
        "created_by": meta.get("generator"),
        "generator_versions_used": versions,
        "hand_edited_files": hand_edited,
        "adopted_stages": [n for n, s in stages.items() if s["adopted"]],
        "stages": stages,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def write(run_dir: Path, dag, manifest) -> dict:
    data = build(run_dir, dag, manifest)
    fd, tmp = tempfile.mkstemp(dir=run_dir, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, run_dir / METADATA_FILENAME)
    (run_dir / LEGACY_FILENAME).unlink(missing_ok=True)
    return data
