import tempfile
import unittest
from pathlib import Path

from planexe_skill.skill import parse_frontmatter, load_skills
from planexe_skill.dag import Dag, DagError
from tests.helpers import make_skill


class FrontmatterTest(unittest.TestCase):
    def test_inline_and_block_lists(self):
        meta, body = parse_frontmatter(
            "---\nname: a\ninputs: [x.txt, y.json]\noutputs:\n  - o_{n}.json\n  - o.md\nest_llm_calls: 3\n---\nhello\n")
        self.assertEqual(meta["name"], "a")
        self.assertEqual(meta["inputs"], ["x.txt", "y.json"])
        self.assertEqual(meta["outputs"], ["o_{n}.json", "o.md"])
        self.assertEqual(meta["est_llm_calls"], 3)
        self.assertEqual(body.strip(), "hello")

    def test_empty_list_and_quoted(self):
        meta, _ = parse_frontmatter('---\ninputs: []\ndescription: "a: b"\n---\n')
        self.assertEqual(meta["inputs"], [])
        self.assertEqual(meta["description"], "a: b")

    def test_missing_frontmatter(self):
        with self.assertRaises(ValueError):
            parse_frontmatter("no frontmatter")


class DagTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_edges_and_order(self):
        make_skill(self.root, "c", ["b.txt", "a.txt"], ["c.txt"])
        make_skill(self.root, "a", ["plan.txt"], ["a.txt"])
        make_skill(self.root, "b", ["a.txt"], ["b.txt"])
        dag = Dag(load_skills(self.root))
        self.assertEqual(dag.order(), ["a", "b", "c"])
        self.assertEqual(dag.deps("c"), {"a", "b"})
        self.assertEqual(dag.downstream("a"), {"b", "c"})
        self.assertEqual(dag.root_inputs(), {"plan.txt"})
        self.assertEqual(dag.producer_of("b.txt"), "b")

    def test_fanout_pattern_producer(self):
        make_skill(self.root, "a", ["plan.txt"], ["part_{n}_raw.json", "all.json"])
        make_skill(self.root, "b", ["all.json"], ["b.txt"])
        dag = Dag(load_skills(self.root))
        self.assertEqual(dag.producer_of("part_7_raw.json"), "a")

    def test_cycle(self):
        make_skill(self.root, "a", ["b.txt"], ["a.txt"])
        make_skill(self.root, "b", ["a.txt"], ["b.txt"])
        with self.assertRaises(DagError) as cm:
            Dag(load_skills(self.root))
        self.assertIn("cycle", str(cm.exception).lower())
        self.assertIn("a", str(cm.exception))

    def test_duplicate_producer(self):
        make_skill(self.root, "a", [], ["x.txt"])
        make_skill(self.root, "b", [], ["x.txt"])
        with self.assertRaises(DagError) as cm:
            Dag(load_skills(self.root))
        self.assertIn("x.txt", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
