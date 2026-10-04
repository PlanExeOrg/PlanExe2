"""Build the stage graph from the files each skill reads and writes."""
from __future__ import annotations

import graphlib

from planexe_skill.skill import Skill


class DagError(Exception):
    pass


class Dag:
    def __init__(self, skills: dict[str, Skill]):
        self.skills = skills
        self._fixed_producer: dict[str, str] = {}
        for s in skills.values():
            for o in s.fixed_outputs():
                if o in self._fixed_producer:
                    raise DagError(f"output file '{o}' is declared by two skills: "
                                   f"'{self._fixed_producer[o]}' and '{s.name}'")
                self._fixed_producer[o] = s.name
        self._deps: dict[str, set[str]] = {}
        for s in skills.values():
            deps = set()
            for i in s.inputs:
                p = self.producer_of(i)
                if p == s.name:
                    raise DagError(f"skill '{s.name}' lists '{i}' as both input and output")
                if p:
                    deps.add(p)
            self._deps[s.name] = deps
        self._order = self._toposort()

    def producer_of(self, filename: str) -> str | None:
        if filename in self._fixed_producer:
            return self._fixed_producer[filename]
        for s in self.skills.values():
            if s.pattern_outputs() and s.produces(filename):
                return s.name
        return None

    def _toposort(self) -> list[str]:
        ts = graphlib.TopologicalSorter(self._deps)
        try:
            ts.prepare()
        except graphlib.CycleError as e:
            cycle = " -> ".join(e.args[1])
            raise DagError(f"dependency cycle between skills: {cycle}") from None
        # Deterministic: Kahn's algorithm, ties broken alphabetically.
        order: list[str] = []
        while ts.is_active():
            ready = sorted(ts.get_ready())
            for r in ready:
                order.append(r)
                ts.done(r)
        return order

    def order(self) -> list[str]:
        return list(self._order)

    def deps(self, name: str) -> set[str]:
        self._check(name)
        return set(self._deps[name])

    def dependents(self, name: str) -> set[str]:
        self._check(name)
        return {n for n, d in self._deps.items() if name in d}

    def downstream(self, name: str) -> set[str]:
        out: set[str] = set()
        stack = [name]
        while stack:
            for d in self.dependents(stack.pop()):
                if d not in out:
                    out.add(d)
                    stack.append(d)
        return out

    def upstream(self, name: str) -> set[str]:
        out: set[str] = set()
        stack = [name]
        while stack:
            for d in self.deps(stack.pop()):
                if d not in out:
                    out.add(d)
                    stack.append(d)
        return out

    def root_inputs(self) -> set[str]:
        return {i for s in self.skills.values() for i in s.inputs if self.producer_of(i) is None}

    def _check(self, name: str) -> None:
        if name not in self.skills:
            known = ", ".join(sorted(self.skills))
            raise DagError(f"unknown stage '{name}'. Known stages: {known}")
