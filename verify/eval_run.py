"""Compare a complete PlanExe-skill run against the PlanExe baseline made from the same prompt.

    python3 -m planexe_skill create runs/euro --plan-raw .verify_work/baselines/20260129_euro_adoption/plan_raw.json
    python3 -m planexe_skill run runs/euro
    python3 -m verify.eval_run runs/euro 20260129_euro_adoption

Every stage's human-facing output(s) are judged blind A/B against the baseline (position-swapped);
structure is checked for every output file. Unlike eval_stage, upstream inputs differ too, so this
measures the end-to-end quality of the whole chain.
Results: verify/results/run_<baseline>.json + a markdown table on stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from planexe_skill import SKILLS_ROOT
from planexe_skill.dag import Dag
from planexe_skill.skill import load_skills
from verify.baselines import DEV_BASELINES, extract_baseline
from verify.eval_stage import RESULTS_DIR, files_to_judge, structure_check
from verify.judge import judge_pair, load_for_judging
from verify.structure import template_headings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("baseline")
    ap.add_argument("--stages", nargs="*", help="only these stages")
    ap.add_argument("--parallel", type=int, default=4, help="concurrent judge pairs")
    args = ap.parse_args(argv)
    run_dir = Path(args.run_dir)
    base = extract_baseline(args.baseline)
    dag = Dag(load_skills(SKILLS_ROOT))
    plan = (base / "plan.txt").read_text()
    template_sources = [extract_baseline(b) for b in DEV_BASELINES]

    stages = [s for s in dag.order() if not args.stages or s in args.stages]
    jobs = []
    structure: dict[str, list[str]] = {}
    for name in stages:
        skill = dag.skills[name]
        templates = {o: template_headings([(d / o).read_text() for d in template_sources if (d / o).exists()])
                     for o in skill.fixed_outputs() if o.endswith(".md")}
        structure[name] = structure_check(skill, base, run_dir, templates)
        if skill.est_llm_calls == 0:
            continue
        desc = f"{name}: {skill.description}\n\n{skill.body.strip()[:3000]}"
        for f in files_to_judge(skill):
            if (base / f).exists() and (run_dir / f).exists():
                jobs.append((name, f, desc))

    def judge(job):
        name, f, desc = job
        try:
            return name, f, judge_pair(plan, desc, f, load_for_judging(base / f), load_for_judging(run_dir / f))
        except Exception as e:  # keep going; report the failure
            return name, f, {"verdict": "error", "error": str(e)}

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        results = list(ex.map(judge, jobs))

    by_stage: dict[str, dict] = {s: {"structure_problems": structure[s], "judgments": {}} for s in stages}
    for name, f, j in results:
        by_stage[name]["judgments"][f] = j
    out = RESULTS_DIR / f"run_{args.baseline}.json"
    out.write_text(json.dumps({"run_dir": str(run_dir), "baseline": args.baseline,
                               "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "stages": by_stage},
                              indent=2, ensure_ascii=False))
    counts = {"new": 0, "tie": 0, "baseline": 0, "error": 0}
    print(f"| stage | file | verdict | new/base | structure |\n|---|---|---|---|---|")
    for s in stages:
        d = by_stage[s]
        sp = d["structure_problems"]
        st = "OK" if not sp else f"{len(sp)} problems: " + "; ".join(sp[:3])
        if not d["judgments"]:
            print(f"| {s} | - | (deterministic) | | {st} |")
        for f, j in d["judgments"].items():
            counts[j["verdict"]] = counts.get(j["verdict"], 0) + 1
            sc = f"{j.get('score_new', 0):.1f}/{j.get('score_baseline', 0):.1f}" if "score_new" in j else j.get("error", "")[:60]
            print(f"| {s} | {f} | {j['verdict']} | {sc} | {st} |")
    print(f"\nTotals: wins {counts['new']}, ties {counts['tie']}, losses {counts['baseline']}, errors {counts['error']}")
    return 0 if counts["baseline"] == 0 and counts["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
