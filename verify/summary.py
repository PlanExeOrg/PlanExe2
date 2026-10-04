"""Render verify/results/*.json as a markdown table in topological order.

    python3 -m verify.summary > verify/results/SUMMARY.md
"""
from __future__ import annotations

import json

from planexe_skill import SKILLS_ROOT
from planexe_skill.dag import Dag
from planexe_skill.skill import load_skills
from verify.eval_stage import RESULTS_DIR

SHORT = {"20250706_gibraltar_tunnel": "gibraltar", "20260516_datacenter_in_france": "datacenter",
         "20260514_cross_border_rail_ticketing": "rail", "20260202_heatwave_resilience": "heatwave",
         "20260129_euro_adoption": "euro", "20250724_battery_breakthrough": "battery"}


def cell(rec: dict) -> str:
    if not rec.get("ran_ok"):
        return "FAILED"
    s = "" if not rec.get("structure_problems") else f" ⚠{len(rec['structure_problems'])}"
    if "identical" in rec:
        return ("identical" if all(rec["identical"].values()) else "differs") + s
    js = rec.get("judgments") or {}
    if not js:
        return "n/a" + s
    parts = []
    for j in js.values():
        sym = {"new": "win", "tie": "tie", "baseline": "LOSS"}[j["verdict"]]
        parts.append(f"{sym} {j['score_new']:.1f}/{j['score_baseline']:.1f}")
    return ", ".join(parts) + s


def main() -> None:
    dag = Dag(load_skills(SKILLS_ROOT))
    rows = []
    cols: list[str] = []
    for name in dag.order():
        p = RESULTS_DIR / f"{name}.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        recs = {r["baseline"]: r for r in data["records"]}
        for b in recs:
            if b not in cols:
                cols.append(b)
        rows.append((name, dag.skills[name].tier, recs))
    print("| stage | tier | " + " | ".join(SHORT.get(c, c) for c in cols) + " |")
    print("|---|---|" + "---|" * len(cols))
    for name, tier, recs in rows:
        print(f"| {name} | {tier} | " + " | ".join(cell(recs[c]) if c in recs else "" for c in cols) + " |")
    print("\nCells: verdict of the blind A/B judge (position-swapped, 2 runs) and mean scores new/baseline (1-10);"
          " ⚠n = structural differences vs baseline; deterministic stages are compared byte-for-byte.")


if __name__ == "__main__":
    main()
