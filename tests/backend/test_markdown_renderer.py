import unittest

from meshchatx.src.backend.markdown_renderer import MarkdownRenderer


class TestMarkdownRenderer(unittest.TestCase):
    def test_basic_render(self):
        self.assertEqual(MarkdownRenderer.render(""), "")
        self.assertIn("<h1", MarkdownRenderer.render("# Hello"))
        self.assertIn("Hello", MarkdownRenderer.render("# Hello"))
        self.assertIn("<strong>Bold</strong>", MarkdownRenderer.render("**Bold**"))
        self.assertIn("<em>Italic</em>", MarkdownRenderer.render("*Italic*"))

    def test_links(self):
        rendered = MarkdownRenderer.render("[Google](https://google.com)")
        self.assertIn('href="https://google.com"', rendered)
        self.assertIn("Google", rendered)

    def test_code_blocks(self):
        code = "```python\nprint('hello')\n```"
        rendered = MarkdownRenderer.render(code)
        self.assertIn("<pre", rendered)
        self.assertIn("<code", rendered)
        self.assertIn("language-python", rendered)
        # Check for escaped characters
        self.assertTrue(
            "print(&#x27;hello&#x27;)" in rendered
            or "print(&#039;hello&#039;)" in rendered,
        )

    def test_lists(self):
        md = "* Item 1\n* Item 2"
        rendered = MarkdownRenderer.render(md)
        self.assertIn("<ul", rendered)
        self.assertIn("Item 1", rendered)
        self.assertIn("Item 2", rendered)

    def test_ordered_lists(self):
        md = "1. First\n2. Second"
        rendered = MarkdownRenderer.render(md)
        self.assertIn("<ol", rendered)
        self.assertIn("First", rendered)

    def test_hr(self):
        md = "---"
        rendered = MarkdownRenderer.render(md)
        self.assertIn("<hr", rendered)

    def test_task_lists(self):
        md = "- [ ] Task 1\n- [x] Task 2"
        rendered = MarkdownRenderer.render(md)
        self.assertIn('type="checkbox"', rendered)
        self.assertIn("checked", rendered)
        self.assertIn("Task 1", rendered)
        self.assertIn("Task 2", rendered)

    def test_strikethrough(self):
        md = "~~strike~~"
        rendered = MarkdownRenderer.render(md)
        self.assertIn("<del>", rendered)
        self.assertIn("strike", rendered)

    def test_paragraphs(self):
        md = "Para 1\n\nPara 2"
        rendered = MarkdownRenderer.render(md)
        self.assertIn("<p", rendered)
        self.assertIn("Para 1", rendered)
        self.assertIn("Para 2", rendered)


if __name__ == "__main__":
    unittest.main()
