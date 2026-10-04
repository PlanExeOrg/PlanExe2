"""Locate and extract PlanExe-web baseline zips."""
from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

from planexe_skill import REPO_ROOT

BASELINE_ZIP_DIR = Path(os.environ.get("PLANEXE_BASELINES", Path.home() / "git" / "PlanExe-web"))
WORK_DIR = REPO_ROOT / ".verify_work"

DEV_BASELINES = [
    "20250706_gibraltar_tunnel",
    "20260516_datacenter_in_france",
    "20260514_cross_border_rail_ticketing",
    "20260202_heatwave_resilience",
]
FINAL_BASELINES = [
    "20260129_euro_adoption",
    "20250724_battery_breakthrough",
    "20250706_gibraltar_tunnel",
    "20260516_datacenter_in_france",
]

# Files that describe the run rather than the plan.
INFRA_FILES = {"usage_metrics.jsonl", "activity_overview.json", "expected_filenames.json", "log.txt",
               "track_activity.jsonl", "pipeline_complete.txt", "planexe_metadata.json"}


def extract_baseline(name: str) -> Path:
    """Extract <name>.zip once into .verify_work/baselines/<name>/ and return that dir."""
    target = WORK_DIR / "baselines" / name
    if target.exists() and any(target.iterdir()):
        return target
    zpath = BASELINE_ZIP_DIR / f"{name}.zip"
    if not zpath.exists():
        raise FileNotFoundError(f"baseline zip not found: {zpath} (set PLANEXE_BASELINES)")
    tmp = WORK_DIR / "baselines" / f".{name}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(tmp)
    inner = tmp / name if (tmp / name).is_dir() else tmp
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(inner), str(target))
    shutil.rmtree(tmp, ignore_errors=True)
    return target
