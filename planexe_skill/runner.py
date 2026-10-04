"""Execute the dirty part of the DAG on a thread pool."""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path

from planexe_skill.context import SkillContext
from planexe_skill.dag import Dag, DagError
from planexe_skill.llm.base import Backend
from planexe_skill.manifest import MANIFEST_DIRNAME, Manifest, existing_outputs
from planexe_skill.progress import Progress
from planexe_skill.skill import Skill


@dataclass
class RunResult:
    ok: bool
    ran: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    blocked: list[str] = field(default_factory=list)
    stopped: bool = False


class StageFailure(Exception):
    pass


class Runner:
    def __init__(self, dag: Dag, run_dir: Path, backend: Backend, workers: int = 4,
                 only: list[str] | None = None, until: list[str] | None = None,
                 force: list[str] | None = None, force_downstream: list[str] | None = None,
                 stream=None, heartbeat_secs: float = 30.0):
        self.dag = dag
        self.run_dir = Path(run_dir)
        self.backend = backend
        self.workers = max(1, workers)
        self.stream = stream or sys.stdout
        self.heartbeat_secs = heartbeat_secs
        self.manifest = Manifest.load(self.run_dir)
        for name in (only or []) + (until or []) + (force or []) + (force_downstream or []):
            if name not in dag.skills:
                raise DagError(f"unknown stage '{name}'. Run `python -m planexe_skill graph` to list stages.")
        if only:
            self.targets = set(only)
        elif until:
            self.targets = set(until)
            for u in until:
                self.targets |= dag.upstream(u)
        else:
            self.targets = set(dag.skills)
        self.only_mode = bool(only)
        self.forced = set(force or [])
        for f in force_downstream or []:
            self.forced |= {f} | dag.downstream(f)
        self.forced &= self.targets
        self.meta_dir = self.run_dir / MANIFEST_DIRNAME
        self.log_dir = self.meta_dir / "logs"
        self._usage_lock = threading.Lock()

    # ---------- planning ----------
    def plan(self) -> list[str]:
        """Stages predicted to run, in topological order."""
        planned: list[str] = []
        for name in self.dag.order():
            if name not in self.targets:
                continue
            skill = self.dag.skills[name]
            st = self.manifest.status(skill, self.run_dir)
            upstream_runs = any(d in planned for d in self.dag.deps(name))
            if name in self.forced or st.dirty or upstream_runs:
                planned.append(name)
        return planned

    def explain(self, name: str) -> list[str]:
        skill = self.dag.skills[name]
        st = self.manifest.status(skill, self.run_dir)
        lines = [f"stage: {name}", f"  tier: {skill.tier}  est_llm_calls: {skill.est_llm_calls}",
                 f"  inputs: {', '.join(skill.inputs) or '-'}",
                 f"  outputs: {', '.join(skill.outputs)}",
                 f"  depends on: {', '.join(sorted(self.dag.deps(name))) or '-'}",
                 f"  dirty: {st.dirty}"]
        lines += [f"    - {r}" for r in st.reasons]
        if st.edited_outputs:
            lines.append(f"  hand-edited outputs (kept): {', '.join(st.edited_outputs)}")
        planned = self.plan()
        if name in planned and not st.dirty:
            ups = [d for d in self.dag.deps(name) if d in planned]
            lines.append(f"  will run because upstream will run: {', '.join(sorted(ups))}")
        return lines

    # ---------- execution ----------
    def _check_root_inputs(self, planned: list[str]) -> None:
        missing = []
        for name in planned:
            for i in self.dag.skills[name].inputs:
                producer = self.dag.producer_of(i)
                will_be_made = producer is not None and (producer in planned)
                if not will_be_made and not (self.run_dir / i).exists():
                    hint = (f"produced by stage '{producer}' which is not selected"
                            if producer else "a root input; create the run with `python -m planexe_skill create`")
                    missing.append(f"  - {i} (needed by '{name}'; {hint})")
        if missing:
            raise StageFailure("cannot start, input files are missing:\n" + "\n".join(sorted(set(missing))))

    def _record_usage(self, stage: str, info: dict) -> None:
        meta = info.get("metadata") or {}
        row = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "success": info.get("success", False),
               "stage": stage, "model": meta.get("model") or self.backend.model_for(info.get("tier", "low")),
               "duration_seconds": round(info.get("duration_seconds", 0.0), 3)}
        for k in ("input_tokens", "output_tokens", "cost_usd", "web_searches"):
            if meta.get(k) is not None:
                row[k] = meta[k]
        with self._usage_lock:
            with open(self.run_dir / "usage_metrics.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")

    def _run_stage(self, skill: Skill, slots: threading.Semaphore, progress: Progress) -> int:
        staging = self.meta_dir / "staging" / skill.name
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"{skill.name}.log"
        log_path.write_text(f"stage {skill.name} started {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")

        def on_call(stage: str, info: dict) -> None:
            progress.llm_call(stage, info)
            self._record_usage(stage, info)

        cache_dir = self.meta_dir / "llm_cache" / skill.name
        if skill.name in self.forced:
            shutil.rmtree(cache_dir, ignore_errors=True)  # forced re-run = fresh answers
        ctx = SkillContext(self.run_dir, staging, skill, self.backend, slots, on_call, log_path, cache_dir)
        skill.module().run(ctx)
        missing = [o for o in skill.fixed_outputs() if not (staging / o).exists()]
        if missing:
            raise StageFailure(f"skill finished without writing declared outputs: {', '.join(missing)}")
        # Replace previous outputs (incl. stale fan-out files) with the staged ones.
        for old in existing_outputs(skill, self.run_dir):
            if skill.produces(old) and not (staging / old).exists():
                (self.run_dir / old).unlink()
        for f in staging.iterdir():
            os.replace(f, self.run_dir / f.name)
        shutil.rmtree(staging, ignore_errors=True)
        self.manifest.record_completed(skill, self.run_dir)
        self.manifest.save()
        shutil.rmtree(cache_dir, ignore_errors=True)
        if ctx.cache_hits:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"resumed: {ctx.cache_hits} of {ctx.llm_calls} LLM calls replayed from the resume cache\n")
        return ctx.llm_calls

    def _failure_report(self, name: str, exc: BaseException) -> str:
        skill = self.dag.skills[name]
        tb = traceback.extract_tb(exc.__traceback__)
        where = ""
        for frame in reversed(tb):
            if str(skill.dir) in frame.filename or "/skills/" in frame.filename:
                where = f"  at: {frame.filename}:{frame.lineno} in {frame.name}\n"
                break
        log = self.log_dir / f"{name}.log"
        with open(log, "a", encoding="utf-8") as f:
            f.write("\n--- FAILURE ---\n" + "".join(traceback.format_exception(exc)))
        msg = str(exc).strip()
        if len(msg) > 2500:
            msg = msg[:2500] + " ..."
        return (f"\n✗ STAGE FAILED: {name}\n"
                f"  error: {type(exc).__name__}: {msg}\n{where}"
                f"  inputs: {', '.join(skill.inputs) or '-'}\n"
                f"  log: {log}\n"
                f"  retry only this stage: python -m planexe_skill run {self.run_dir} --only {name}\n"
                f"  resume the whole run:  python -m planexe_skill run {self.run_dir}\n")

    def run(self) -> RunResult:
        planned = self.plan()
        result = RunResult(ok=True)
        # Adopt outputs that exist but were never recorded (e.g. seeded from a PlanExe run).
        for name in self.dag.order():
            if name in self.targets and name not in planned and self.manifest.entry(name) is None:
                self.manifest.record_completed(self.dag.skills[name], self.run_dir, adopted=True)
        self.manifest.save()
        if not planned:
            print("Nothing to do: all selected stages are up to date.", file=self.stream)
            return result
        self._check_root_inputs(planned)

        progress = Progress(self.dag, planned, self.workers, self.run_dir, self.stream, self.heartbeat_secs)
        slots = threading.Semaphore(self.workers)
        stop_file = self.meta_dir / "stop"
        stop_file.unlink(missing_ok=True)
        state: dict[str, str] = {n: "pending" for n in planned}
        futures: dict[Future, str] = {}
        progress.start()
        # More stage threads than LLM slots, so cheap deterministic stages never wait behind LLM calls.
        pool = ThreadPoolExecutor(max_workers=max(8, self.workers * 3))
        try:
            while True:
                if stop_file.exists():
                    result.stopped = True
                for name in planned:
                    if state[name] != "pending" or result.stopped:
                        continue
                    deps = [d for d in self.dag.deps(name) if d in state]
                    if any(state[d] in ("failed", "blocked") for d in deps):
                        state[name] = "blocked"
                        result.blocked.append(name)
                        progress.stage_finished(name, "blocked", "an upstream stage failed")
                        continue
                    if not all(state[d] in ("done", "skipped") for d in deps):
                        continue
                    skill = self.dag.skills[name]
                    if name not in self.forced and not self.manifest.status(skill, self.run_dir).dirty:
                        state[name] = "skipped"
                        result.skipped.append(name)
                        progress.stage_finished(name, "skipped", "up to date")
                        continue
                    state[name] = "running"
                    progress.stage_started(name)
                    futures[pool.submit(self._run_stage, skill, slots, progress)] = name
                if not futures:
                    break
                finished, _ = wait(list(futures), return_when=FIRST_COMPLETED, timeout=2.0)
                for fut in finished:
                    name = futures.pop(fut)
                    exc = fut.exception()
                    if exc is None:
                        state[name] = "done"
                        result.ran.append(name)
                        progress.stage_finished(name, "done")
                    else:
                        state[name] = "failed"
                        result.failed[name] = str(exc)
                        progress.stage_finished(name, "failed")
                        print(self._failure_report(name, exc), file=self.stream, flush=True)
        except KeyboardInterrupt:
            print("\nInterrupted: waiting for running stages to stop. Re-run the same command to resume.",
                  file=self.stream, flush=True)
            result.stopped = True
            pool.shutdown(wait=False, cancel_futures=True)
            raise
        finally:
            pool.shutdown(wait=True)
            progress.stop()
        result.ok = not result.failed and not result.blocked and not result.stopped
        print(self._summary(result, progress), file=self.stream, flush=True)
        return result

    def _summary(self, r: RunResult, progress: Progress) -> str:
        s = progress.summary()
        lines = [f"\nRun finished in {s['elapsed_seconds']:.0f}s: {len(r.ran)} ran, {len(r.skipped)} up to date, "
                 f"{len(r.failed)} failed, {len(r.blocked)} blocked, {s['llm_calls_done']} llm calls."]
        if r.stopped:
            lines.append("Stopped early (stop requested). Re-run to continue.")
        if r.failed:
            lines.append("Failed: " + ", ".join(r.failed) + f"  (logs in {self.log_dir})")
            lines.append(f"Fix the cause, then resume with: python -m planexe_skill run {self.run_dir}")
        return "\n".join(lines)
