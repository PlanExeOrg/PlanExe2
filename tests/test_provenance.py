import io
import json
import tempfile
import unittest
from pathlib import Path

from planexe_skill.dag import Dag
from planexe_skill.llm.fake import FakeBackend
from planexe_skill.provenance import PROVENANCE_FILENAME, _repo_from_remote, generator_info
from planexe_skill.runner import Runner
from planexe_skill.skill import load_skills
from tests.helpers import make_skill


class ProvenanceTest(unittest.TestCase):
    def test_repo_from_remote(self):
        self.assertEqual(_repo_from_remote("git@github.com:PlanExeOrg/PlanExe2.git"), "PlanExeOrg/PlanExe2")
        self.assertEqual(_repo_from_remote("https://github.com/PlanExeOrg/PlanExe2"), "PlanExeOrg/PlanExe2")

    def test_generator_info_shape(self):
        g = generator_info()
        self.assertEqual(g["name"], "PlanExe2")
        self.assertTrue(g["version"])

    def test_runner_writes_provenance_and_detects_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run_dir = base / "run"
            run_dir.mkdir()
            (run_dir / "plan.txt").write_text("P")
            (run_dir / "start_time.json").write_text(json.dumps({"server_iso_utc": "2031-01-15T00:00:00Z"}))
            make_skill(base / "skills", "a", ["plan.txt"], ["a.txt"])
            make_skill(base / "skills", "b", ["a.txt"], ["b.txt"])
            dag = Dag(load_skills(base / "skills"))
            Runner(dag, run_dir, FakeBackend(), stream=io.StringIO(), heartbeat_secs=999).run()
            p = json.loads((run_dir / PROVENANCE_FILENAME).read_text())
            self.assertEqual(p["plan_start_date"], "2031-01-15")  # plan dated in the future
            self.assertEqual(set(p["stages"]), {"a", "b"})
            self.assertEqual(p["stages"]["a"]["generator"]["name"], "PlanExe2")
            self.assertEqual(p["hand_edited_files"], [])
            (run_dir / "a.txt").write_text("edited by hand")
            Runner(dag, run_dir, FakeBackend(), stream=io.StringIO(), heartbeat_secs=999).run()
            p = json.loads((run_dir / PROVENANCE_FILENAME).read_text())
            self.assertEqual(p["hand_edited_files"], [{"stage": "a", "file": "a.txt"}])


if __name__ == "__main__":
    unittest.main()
