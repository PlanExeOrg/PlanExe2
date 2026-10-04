import unittest

from planexe_skill.shared.markdown_html import inline, render


class MarkdownHtmlTest(unittest.TestCase):
    def test_heading_and_paragraph(self):
        self.assertEqual(render("# Title\n\nHello **bold** and *it*."),
                         "<h1>Title</h1>\n<p>Hello <strong>bold</strong> and <em>it</em>.</p>")

    def test_list_nested(self):
        html = render("- a\n- b\n  - c\n- d")
        self.assertEqual(html, "<ul>\n<li>a</li>\n<li>b\n<ul>\n<li>c</li>\n</ul>\n</li>\n<li>d</li>\n</ul>")

    def test_ordered_list(self):
        self.assertEqual(render("1. x\n2. y"), "<ol>\n<li>x</li>\n<li>y</li>\n</ol>")

    def test_list_directly_after_paragraph(self):
        self.assertIn("<ul>", render("**Items:**\n- a\n- b"))

    def test_table(self):
        html = render("| A | B |\n|---|---|\n| 1 | x \\| y |")
        self.assertIn("<th>A</th>", html)
        self.assertIn("<td>x | y</td>", html)

    def test_escaping(self):
        self.assertEqual(inline("a < b & c &amp; <br>"), "a &lt; b &amp; c &amp; <br>")

    def test_code(self):
        self.assertEqual(inline("use `a<b>` now"), "use <code>a&lt;b&gt;</code> now")
        self.assertIn('<pre><code class="language-csv">a,b\n</code></pre>', render("```csv\na,b\n```"))

    def test_link(self):
        self.assertEqual(inline("[x](https://e.com/a_b)"), '<a href="https://e.com/a_b">x</a>')

    def test_underscore_in_word_not_emphasis(self):
        self.assertEqual(inline("snake_case_name"), "snake_case_name")

    def test_blockquote(self):
        self.assertEqual(render("> **Warn**\n>\n> text"),
                         "<blockquote>\n<p><strong>Warn</strong></p>\n<p>text</p>\n</blockquote>")

    def test_hr(self):
        self.assertEqual(render("a\n\n---\n\nb"), "<p>a</p>\n<hr />\n<p>b</p>")


if __name__ == "__main__":
    unittest.main()
