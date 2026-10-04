import unittest

from verify.structure import compare_markdown, diff_shapes, shape, template_headings


class StructureTest(unittest.TestCase):
    def test_same_shape_different_lengths(self):
        a = {"items": [{"x": 1, "y": "a"}], "metadata": {"m": 1}}
        b = {"items": [{"x": 2, "y": "b"}, {"x": 3, "y": None}], "metadata": {"other": 2}}
        self.assertEqual(diff_shapes(shape(a), shape(b)), [])

    def test_missing_and_extra_keys(self):
        a = {"items": [{"x": 1, "y": "a"}]}
        b = {"items": [{"x": 1, "z": "a"}]}
        problems = diff_shapes(shape(a), shape(b))
        self.assertIn("$.items[].y: missing key", problems)
        self.assertIn("$.items[].z: extra key", problems)

    def test_type_mismatch(self):
        self.assertEqual(diff_shapes(shape({"a": "s"}), shape({"a": 1})), ["$.a: type number != expected string"])

    def test_template_headings(self):
        t1 = "# Title\n## Risks\n## Foo specific\n"
        t2 = "# Title\n## Risks\n## Bar specific\n"
        tpl = template_headings([t1, t2])
        self.assertEqual(tpl, [(1, "Title"), (2, "Risks")])
        self.assertEqual(compare_markdown(tpl, "# Title\n## Other\n"), ["missing heading ## Risks"])


if __name__ == "__main__":
    unittest.main()
