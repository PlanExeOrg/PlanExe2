import tempfile
import unittest
from pathlib import Path

from planexe_skill.dag import Dag
from planexe_skill.manifest import Manifest, hash_dir, existing_outputs
from planexe_skill.skill import load_skills
from tests.helpers import make_skill


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.skills_root = base / "skills"
        self.run_dir = base / "run"
        self.run_dir.mkdir()
        make_skill(self.skills_root, "a", ["plan.txt"], ["a.txt"])
        make_skill(self.skills_root, "b", ["a.txt"], ["b_{n}_raw.json", "b.txt"])
        self.skills = load_skills(self.skills_root)
        self.dag = Dag(self.skills)
        (self.run_dir / "plan.txt").write_text("p")

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, m, name):
        m.record_completed(self.skills[name], self.run_dir)

    def test_missing_output_is_dirty(self):
        m = Manifest.load(self.run_dir)
        st = m.status(self.skills["a"], self.run_dir)
        self.assertTrue(st.dirty)
        self.assertIn("missing output a.txt", st.reasons[0])

    def test_adopt_existing_outputs(self):
        (self.run_dir / "a.txt").write_text("x")
        m = Manifest.load(self.run_dir)
        st = m.status(self.skills["a"], self.run_dir)
        self.assertFalse(st.dirty)
        self.assertTrue(st.adoptable)

    def test_clean_after_record_and_dirty_after_input_change(self):
        (self.run_dir / "a.txt").write_text("x")
        m = Manifest.load(self.run_dir)
        self.record(m, "a")
        m.save()
        m = Manifest.load(self.run_dir)
        self.assertFalse(m.status(self.skills["a"], self.run_dir).dirty)
        (self.run_dir / "plan.txt").write_text("changed")
        st = m.status(self.skills["a"], self.run_dir)
        self.assertTrue(st.dirty)
        self.assertIn("plan.txt", st.reasons[0])

    def test_edited_output_keeps_stage_clean(self):
        (self.run_dir / "a.txt").write_text("x")
        m = Manifest.load(self.run_dir)
        self.record(m, "a")
        (self.run_dir / "a.txt").write_text("hand edited")
        st = m.status(self.skills["a"], self.run_dir)
        self.assertFalse(st.dirty)
        self.assertEqual(st.edited_outputs, ["a.txt"])

    def test_skill_change_is_dirty(self):
        (self.run_dir / "a.txt").write_text("x")
        m = Manifest.load(self.run_dir)
        self.record(m, "a")
        (self.skills_root / "a" / "SKILL.md").write_text(
            (self.skills_root / "a" / "SKILL.md").read_text() + "\nmore\n")
        st = m.status(self.skills["a"], self.run_dir)
        self.assertTrue(st.dirty)
        self.assertIn("skill definition changed", st.reasons[0])

    def test_fanout_outputs_recorded(self):
        (self.run_dir / "a.txt").write_text("x")
        (self.run_dir / "b.txt").write_text("x")
        (self.run_dir / "b_1_raw.json").write_text("{}")
        (self.run_dir / "b_2_raw.json").write_text("{}")
        self.assertEqual(existing_outputs(self.skills["b"], self.run_dir),
                         ["b.txt", "b_1_raw.json", "b_2_raw.json"])
        m = Manifest.load(self.run_dir)
        self.record(m, "b")
        (self.run_dir / "b_2_raw.json").unlink()
        st = m.status(self.skills["b"], self.run_dir)
        self.assertTrue(st.dirty)
        self.assertIn("b_2_raw.json", st.reasons[0])

    def test_hash_dir_ignores_pycache(self):
        h1 = hash_dir(self.skills_root / "a")
        (self.skills_root / "a" / "__pycache__").mkdir()
        (self.skills_root / "a" / "__pycache__" / "x.pyc").write_text("junk")
        self.assertEqual(h1, hash_dir(self.skills_root / "a"))



class SharedUsesTest(unittest.TestCase):
    def test_uses_file_changes_skill_hash(self):
        from planexe_skill.manifest import skill_hash
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root / "skills", "a", [], ["a.txt"])
            shared = root / "shared.py"
            shared.write_text("x = 1\n")
            skill = load_skills(root / "skills")["a"]
            skill.uses = [str(shared)]  # absolute path also works: REPO_ROOT / abs == abs
            h1 = skill_hash(skill)
            shared.write_text("x = 2\n")
            self.assertNotEqual(h1, skill_hash(skill))


if __name__ == "__main__":
    unittest.main()
