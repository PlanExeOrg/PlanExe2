"""Progress reporting with an ETA that respects the DAG's critical path.

The ETA is computed by simulating the remaining stages on N workers, using per-stage
durations remembered from earlier runs (~/.planexe_skill/timings.json) or, when a stage
has never run, `est_llm_calls * seconds_per_call(tier)`.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

from planexe_skill.dag import Dag

DEFAULT_SECS_PER_CALL = {"high": 45.0, "mid": 30.0, "low": 20.0}


def history_path() -> Path:
    home = Path(os.environ.get("PLANEXE_SKILL_HOME", Path.home() / ".planexe_skill"))
    return home / "timings.json"


def load_history() -> dict:
    p = history_path()
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {"stages": {}, "secs_per_call": {}}


def save_history(h: dict) -> None:
    p = history_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(h, indent=2, sort_keys=True))
        os.replace(tmp, p)
    except OSError:
        pass


def fmt_secs(s: float) -> str:
    s = int(max(0, s))
    if s >= 3600:
        return f"{s // 3600}h{(s % 3600) // 60:02d}m"
    if s >= 60:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s}s"


class Progress:
    def __init__(self, dag: Dag, planned: list[str], workers: int, run_dir: Path,
                 stream=None, heartbeat_secs: float = 30.0, history: dict | None = None):
        self.dag = dag
        self.planned = list(planned)
        self.workers = max(1, workers)
        self.run_dir = run_dir
        self.stream = stream or sys.stdout
        self.heartbeat_secs = heartbeat_secs
        self.history = history if history is not None else load_history()
        self.state: dict[str, str] = {s: "pending" for s in planned}
        self.started: dict[str, float] = {}
        self.finished: dict[str, float] = {}
        self.calls: dict[str, int] = {s: 0 for s in planned}
        self.call_secs: dict[str, list[float]] = {"high": [], "mid": [], "low": []}
        self.t0 = time.time()
        self._lock = threading.RLock()
        self._last_print = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---------- estimates ----------
    def secs_per_call(self, tier: str) -> float:
        observed = self.call_secs.get(tier) or []
        if len(observed) >= 3:
            recent = observed[-20:]
            return sum(recent) / len(recent)
        hist = self.history.get("secs_per_call", {}).get(tier)
        return float(hist or DEFAULT_SECS_PER_CALL.get(tier, 30.0))

    def est_duration(self, stage: str) -> float:
        h = self.history.get("stages", {}).get(stage)
        if h and h.get("durations"):
            d = h["durations"][-3:]
            return sum(d) / len(d)
        skill = self.dag.skills[stage]
        if skill.est_llm_calls <= 0:
            return 1.0
        par = int(skill.meta.get("parallel_llm", 1) or 1)
        par = max(1, min(par, self.workers, skill.est_llm_calls))
        return skill.est_llm_calls * self.secs_per_call(skill.tier) / par

    def est_total_calls(self) -> int:
        total = 0
        for s in self.planned:
            if self.state[s] in ("done", "failed"):
                total += self.calls[s]
            elif self.state[s] in ("skipped", "blocked"):
                continue
            else:
                total += max(self.calls[s], self.dag.skills[s].est_llm_calls)
        return total

    def eta_seconds(self) -> float:
        """List-scheduling simulation of the remaining DAG on `workers` parallel slots."""
        now = time.time()
        remaining = {s for s in self.planned if self.state[s] in ("pending", "running")}
        if not remaining:
            return 0.0
        dur = {}
        for s in remaining:
            d = self.est_duration(s)
            if self.state[s] == "running":
                elapsed = now - self.started.get(s, now)
                d = max(d - elapsed, d * 0.05, 1.0)
            dur[s] = d
        deps = {s: (self.dag.deps(s) & remaining) for s in remaining}
        t = 0.0
        finish: dict[str, float] = {}
        running: list[tuple[float, str]] = []
        # Start currently running stages first.
        order = sorted(remaining, key=lambda s: (self.state[s] != "running", self.dag.order().index(s)))
        waiting = list(order)
        while waiting or running:
            started_any = True
            while started_any and len(running) < self.workers:
                started_any = False
                for s in list(waiting):
                    if all(d in finish for d in deps[s]):
                        start = max([t] + [finish[d] for d in deps[s]])
                        running.append((start + dur[s], s))
                        waiting.remove(s)
                        started_any = True
                        if len(running) >= self.workers:
                            break
            if not running:
                break  # unreachable unless deps are inconsistent
            running.sort()
            end, s = running.pop(0)
            finish[s] = end
            t = max(t, end)
        return max(finish.values()) if finish else 0.0

    # ---------- events ----------
    def stage_started(self, stage: str) -> None:
        with self._lock:
            self.state[stage] = "running"
            self.started[stage] = time.time()
        self._emit(f"▶ {stage}")

    def stage_finished(self, stage: str, status: str, note: str = "") -> None:
        with self._lock:
            self.state[stage] = status
            self.finished[stage] = time.time()
            dur = self.finished[stage] - self.started.get(stage, self.finished[stage])
            if status == "done" and stage in self.started:
                h = self.history.setdefault("stages", {}).setdefault(stage, {"durations": []})
                h["durations"] = (h["durations"] + [round(dur, 1)])[-5:]
        symbol = {"done": "✓", "failed": "✗", "skipped": "·", "blocked": "⊘"}.get(status, "?")
        timing = f" ({fmt_secs(dur)}, {self.calls.get(stage, 0)} llm calls)" if stage in self.started else ""
        self._emit(f"{symbol} {stage} {status}{timing}{(' — ' + note) if note else ''}")

    def llm_call(self, stage: str, info: dict) -> None:
        with self._lock:
            self.calls[stage] = self.calls.get(stage, 0) + 1
            if info.get("success"):
                self.call_secs.setdefault(info["tier"], []).append(info["duration_seconds"])
            self._write_json()

    # ---------- output ----------
    def summary(self) -> dict:
        with self._lock:
            counts: dict[str, int] = {}
            for st in self.state.values():
                counts[st] = counts.get(st, 0) + 1
            done = counts.get("done", 0) + counts.get("skipped", 0)
            return {
                "stages_total": len(self.planned),
                "stages_done": done,
                "stages_failed": counts.get("failed", 0),
                "stages_blocked": counts.get("blocked", 0),
                "running": sorted(s for s, st in self.state.items() if st == "running"),
                "llm_calls_done": sum(self.calls.values()),
                "llm_calls_estimated_total": self.est_total_calls(),
                "elapsed_seconds": round(time.time() - self.t0, 1),
                "eta_seconds": round(self.eta_seconds(), 1),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "stages": dict(self.state),
            }

    def status_line(self) -> str:
        s = self.summary()
        running = ", ".join(
            f"{r} {fmt_secs(time.time() - self.started.get(r, time.time()))}" for r in s["running"])
        pct = 100.0 * s["stages_done"] / max(1, s["stages_total"])
        return (f"[{s['stages_done']}/{s['stages_total']} stages {pct:3.0f}% | llm {s['llm_calls_done']}/"
                f"~{s['llm_calls_estimated_total']} | elapsed {fmt_secs(s['elapsed_seconds'])} | "
                f"ETA {fmt_secs(s['eta_seconds'])}]" + (f" running: {running}" if running else ""))

    def _write_json(self) -> None:
        p = self.run_dir / ".planexe_skill" / "progress.json"
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.summary(), indent=2))
            os.replace(tmp, p)
        except OSError:
            pass

    def _emit(self, event: str) -> None:
        with self._lock:
            line = f"{event:<45} {self.status_line()}"
            print(line, file=self.stream, flush=True)
            self._last_print = time.time()
            self._write_json()

    def _heartbeat(self) -> None:
        while not self._stop.wait(5.0):
            if time.time() - self._last_print >= self.heartbeat_secs:
                self._emit("…")

    def start(self) -> None:
        self._emit("start")
        self._thread = threading.Thread(target=self._heartbeat, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        with self._lock:
            for tier, secs in self.call_secs.items():
                if len(secs) >= 3:
                    self.history.setdefault("secs_per_call", {})[tier] = round(sum(secs) / len(secs), 2)
            save_history(self.history)
            self._write_json()
