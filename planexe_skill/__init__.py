"""PlanExe2: PlanExe's planning pipeline as skills run by a lightweight DAG."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"
