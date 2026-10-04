"""Dev-only porting aid. Run with PlanExe's venv (NOT a runtime dependency of PlanExe-skill):

    cd ~/git/PlanExeGroup/PlanExe/worker_plan
    .venv/bin/python ~/git/PlanExe-skill/tools/extract_planexe_module.py \
        worker_plan_internal.assume.identify_purpose OUT_DIR

Writes OUT_DIR/schemas/<Model>.json (pydantic JSON schema) and OUT_DIR/prompts/<CONST>.txt for every
module-level string constant whose name contains PROMPT, so skills can carry them verbatim.
"""
import importlib
import json
import sys
from pathlib import Path

from pydantic import BaseModel


def main() -> None:
    module_name, out = sys.argv[1], Path(sys.argv[2])
    m = importlib.import_module(module_name)
    (out / "schemas").mkdir(parents=True, exist_ok=True)
    (out / "prompts").mkdir(parents=True, exist_ok=True)
    for k, v in vars(m).items():
        if isinstance(v, type) and issubclass(v, BaseModel) and v is not BaseModel and v.__module__ == m.__name__:
            (out / "schemas" / f"{k}.json").write_text(json.dumps(v.model_json_schema(), indent=2, ensure_ascii=False))
        elif isinstance(v, str) and "PROMPT" in k.upper() and len(v) > 40:
            (out / "prompts" / f"{k}.txt").write_text(v)
    print(f"{module_name}: wrote to {out}")


if __name__ == "__main__":
    main()
