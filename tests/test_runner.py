import io
import tempfile
import textwrap
import unittest
from pathlib import Path

from planexe_skill.dag import Dag
from planexe_skill.llm.fake import FakeBackend
from planexe_skill.runner import Runner, StageFailure
from planexe_skill.skill import load_skills
from tests.helpers import make_skill

LLM_RUN = textwrap.dedent("""\
    def run(ctx):
        r = ctx.llm("sys", ctx.read_text("plan.txt"), {"type": "object", "properties": {"v": {"type": "string"}}})
        ctx.write_json("a.json", r.data)
    """)

FAIL_RUN = textwrap.dedent("""\
    def run(ctx):
        raise RuntimeError("boom in skill")
    """)

FANOUT_RUN = textwrap.dedent("""\
    def run(ctx):
        n = int(ctx.read_text("count.txt"))
        for i in range(1, n + 1):
            ctx.write_text(f"part_{i}_raw.json", str(i))
        ctx.write_text("parts.txt", str(n))
    """)


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.skills = base / "skills"
        self.run_dir = base / "run"
        self.run_dir.mkdir()
        (self.run_dir / "plan.txt").write_text("P")

    def tearDown(self):
        self.tmp.cleanup()

    def runner(self, **kw):
        out = io.StringIO()
        r = Runner(Dag(load_skills(self.skills)), self.run_dir, FakeBackend(), stream=out, heartbeat_secs=999, **kw)
        return r, out

    def chain(self):
        make_skill(self.skills, "a", ["plan.txt"], ["a.txt"])
        make_skill(self.skills, "b", ["a.txt"], ["b.txt"])
        make_skill(self.skills, "c", ["b.txt"], ["c.txt"])

    def test_runs_everything_then_nothing(self):
        self.chain()
        r, _ = self.runner()
        res = r.run()
        self.assertTrue(res.ok)
        self.assertEqual(res.ran, ["a", "b", "c"])
        self.assertEqual((self.run_dir / "c.txt").read_text(), "c:b:a:P")
        r, out = self.runner()
        self.assertEqual(r.plan(), [])
        r.run()
        self.assertIn("Nothing to do", out.getvalue())

    def test_edit_output_reruns_downstream_only(self):
        self.chain()
        self.runner()[0].run()
        (self.run_dir / "a.txt").write_text("EDITED")
        r, _ = self.runner()
        self.assertEqual(r.plan(), ["b", "c"])
        r.run()
        self.assertEqual((self.run_dir / "a.txt").read_text(), "EDITED")
        self.assertEqual((self.run_dir / "c.txt").read_text(), "c:b:EDITED")

    def test_deleted_output_reruns_that_stage(self):
        self.chain()
        self.runner()[0].run()
        (self.run_dir / "b.txt").unlink()
        r, _ = self.runner()
        res = r.run()
        self.assertEqual(res.ran, ["b"])
        self.assertEqual(res.skipped, ["c"])  # b regenerated identical output -> c stays clean

    def test_force_downstream(self):
        self.chain()
        self.runner()[0].run()
        r, _ = self.runner(force_downstream=["b"])
        self.assertEqual(r.plan(), ["b", "c"])

    def test_adopts_seeded_outputs(self):
        self.chain()
        (self.run_dir / "a.txt").write_text("seed")
        (self.run_dir / "b.txt").write_text("seed-b")
        r, _ = self.runner()
        self.assertEqual(r.plan(), ["c"])
        r.run()
        self.assertEqual((self.run_dir / "c.txt").read_text(), "c:seed-b")

    def test_failure_blocks_dependents_not_siblings(self):
        make_skill(self.skills, "a", ["plan.txt"], ["a.txt"], run_py=FAIL_RUN)
        make_skill(self.skills, "b", ["a.txt"], ["b.txt"])
        make_skill(self.skills, "x", ["plan.txt"], ["x.txt"])
        r, out = self.runner()
        res = r.run()
        self.assertFalse(res.ok)
        self.assertIn("a", res.failed)
        self.assertEqual(res.blocked, ["b"])
        self.assertIn("x", res.ran)
        text = out.getvalue()
        self.assertIn("STAGE FAILED: a", text)
        self.assertIn("boom in skill", text)
        self.assertIn("run.py", text)
        self.assertIn("--only a", text)
        self.assertFalse((self.run_dir / "a.txt").exists())

    def test_llm_call_and_usage(self):
        make_skill(self.skills, "a", ["plan.txt"], ["a.json"], run_py=LLM_RUN, est_llm_calls=1)
        r, _ = self.runner()
        res = r.run()
        self.assertTrue(res.ok, res.failed)
        self.assertEqual((self.run_dir / "a.json").read_text().strip().replace(" ", "").replace("\n", ""),
                         '{"v":"text"}')
        self.assertTrue((self.run_dir / "usage_metrics.jsonl").exists())
        self.assertTrue((self.run_dir / ".planexe_skill" / "progress.json").exists())

    def test_undeclared_read_is_an_error(self):
        make_skill(self.skills, "a", [], ["a.txt"], run_py="def run(ctx):\n    ctx.read_text('plan.txt')\n")
        r, out = self.runner()
        res = r.run()
        self.assertIn("not listed in its SKILL.md inputs", res.failed["a"])

    def test_missing_root_input(self):
        make_skill(self.skills, "a", ["nope.txt"], ["a.txt"])
        r, _ = self.runner()
        with self.assertRaises(StageFailure) as cm:
            r.run()
        self.assertIn("nope.txt", str(cm.exception))

    def test_fanout_stale_files_removed(self):
        make_skill(self.skills, "f", ["count.txt"], ["part_{n}_raw.json", "parts.txt"], run_py=FANOUT_RUN)
        (self.run_dir / "count.txt").write_text("3")
        self.runner()[0].run()
        self.assertTrue((self.run_dir / "part_3_raw.json").exists())
        (self.run_dir / "count.txt").write_text("2")
        self.runner()[0].run()
        self.assertTrue((self.run_dir / "part_2_raw.json").exists())
        self.assertFalse((self.run_dir / "part_3_raw.json").exists())

    def test_eta_positive_while_pending(self):
        from planexe_skill.progress import Progress
        self.chain()
        dag = Dag(load_skills(self.skills))
        p = Progress(dag, dag.order(), 4, self.run_dir, io.StringIO(), history={"stages": {
            "a": {"durations": [10]}, "b": {"durations": [20]}, "c": {"durations": [30]}}})
        self.assertAlmostEqual(p.eta_seconds(), 60.0)



class ResumeCacheTest(unittest.TestCase):
    def test_failed_stage_resumes_completed_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run_dir = base / "run"
            run_dir.mkdir()
            (run_dir / "plan.txt").write_text("P")
            (base / "flag").write_text("fail")
            run_py = textwrap.dedent(f"""\
                from pathlib import Path
                def run(ctx):
                    for i in range(3):
                        ctx.llm("sys", f"q{{i}}", {{"type": "object", "properties": {{"v": {{"type": "string"}}}}}})
                    if Path({str(base / 'flag')!r}).read_text() == "fail":
                        raise RuntimeError("boom after 3 calls")
                    ctx.write_text("a.txt", "ok")
                """)
            make_skill(base / "skills", "a", ["plan.txt"], ["a.txt"], run_py=run_py, est_llm_calls=3)
            backend = FakeBackend()
            dag = Dag(load_skills(base / "skills"))
            Runner(dag, run_dir, backend, stream=io.StringIO(), heartbeat_secs=999).run()
            self.assertEqual(len(backend.calls), 3)
            (base / "flag").write_text("ok")
            res = Runner(dag, run_dir, backend, stream=io.StringIO(), heartbeat_secs=999).run()
            self.assertTrue(res.ok)
            self.assertEqual(len(backend.calls), 3)  # all 3 calls replayed from the resume cache
            self.assertFalse((run_dir / ".planexe_skill" / "llm_cache" / "a").exists())



class LengthBudgetTest(unittest.TestCase):
    def test_budget_applied_to_text_fields_only(self):
        from planexe_skill.context import with_length_budget
        schema = {"$defs": {"I": {"type": "object", "properties": {
            "title": {"type": "string", "description": "Title."},
            "why": {"type": "string", "description": "Concise rationale (30-50 words)."},
            "kind": {"type": "string", "enum": ["a", "b"]},
            "n": {"type": "integer"},
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}]}}}},
            "type": "object", "properties": {"items": {"type": "array", "items": {"$ref": "#/$defs/I"}}}}
        out = with_length_budget(schema, 50)
        props = out["$defs"]["I"]["properties"]
        self.assertEqual(props["title"]["description"], "Title. At most 50 words.")
        self.assertEqual(props["why"]["description"], "Concise rationale (30-50 words).")
        self.assertNotIn("description", props["kind"])
        self.assertNotIn("description", props["n"])
        self.assertEqual(props["note"]["description"], "At most 50 words.")
        self.assertNotIn("At most", schema["$defs"]["I"]["properties"]["title"]["description"])



class AuthStopTest(unittest.TestCase):
    def test_auth_error_stops_run(self):
        from planexe_skill.llm.base import LLMAuthError
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run_dir = base / "run"
            run_dir.mkdir()
            (run_dir / "plan.txt").write_text("P")
            make_skill(base / "skills", "a", ["plan.txt"], ["a.txt"], run_py="def run(ctx):\n    ctx.llm('s', 'u')\n")
            make_skill(base / "skills", "b", ["a.txt"], ["b.txt"])

            class Revoked(FakeBackend):
                def complete(self, *a, **k):
                    raise LLMAuthError("401 OAuth access token has been revoked")
            out = io.StringIO()
            res = Runner(Dag(load_skills(base / "skills")), run_dir, Revoked(), stream=out, heartbeat_secs=999).run()
            self.assertTrue(res.stopped)
            self.assertIn("claude auth login", out.getvalue())


if __name__ == "__main__":
    unittest.main()
