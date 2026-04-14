import time
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

    def test_render_none_and_empty(self):
        self.assertEqual(MarkdownRenderer.render(None), "")
        self.assertEqual(MarkdownRenderer.render(""), "")
        r = MarkdownRenderer.render("   ")
        self.assertIsInstance(r, str)

    def test_xss_script_tags(self):
        cases = [
            "<script>alert(1)</script>",
            "<SCRIPT>alert(1)</SCRIPT>",
            '<script src="evil.js"></script>',
            "</script><script>alert(1)</script>",
        ]
        for s in cases:
            r = MarkdownRenderer.render(s)
            self.assertNotIn("<script>", r, msg=s)
            self.assertNotIn("</script>", r, msg=s)
            self.assertIn("&lt;", r, msg=s)

    def test_xss_event_handlers(self):
        cases = [
            '<img src="x" onerror="alert(1)">',
            '<body onload="alert(1)">',
            '<a href="x" onmouseover="alert(1)">x</a>',
            '<svg onload="alert(1)">',
        ]
        for s in cases:
            r = MarkdownRenderer.render(s)
            self.assertNotIn("<img", r, msg=s)
            self.assertNotIn("<body", r, msg=s)
            self.assertNotIn("<svg", r, msg=s)
            self.assertNotIn("<a ", r, msg=s)
            self.assertIn("&lt;", r, msg=s)

    def test_xss_link_href_javascript(self):
        r = MarkdownRenderer.render("[click](javascript:alert(1))")
        self.assertNotIn("javascript:", r)
        self.assertIn('href="#"', r)

    def test_xss_link_href_data(self):
        r = MarkdownRenderer.render("[click](data:text/html,<script>alert(1)</script>)")
        self.assertNotIn("data:", r)
        self.assertIn('href="#"', r)

    def test_xss_link_href_vbscript(self):
        r = MarkdownRenderer.render("[click](vbscript:msgbox(1))")
        self.assertNotIn("vbscript:", r)
        self.assertIn('href="#"', r)

    def test_safe_links_preserved(self):
        r = MarkdownRenderer.render("[link](https://example.com/path)")
        self.assertIn('href="https://example.com/path"', r)
        r = MarkdownRenderer.render("[link](/relative)")
        self.assertIn('href="/relative"', r)
        r = MarkdownRenderer.render("[link](#anchor)")
        self.assertIn('href="#anchor"', r)

    def test_redos_safe_repeated_markers(self):
        t0 = time.perf_counter()
        MarkdownRenderer.render("*" * 8000)
        MarkdownRenderer.render("#" * 8000)
        MarkdownRenderer.render("`" * 8000)
        MarkdownRenderer.render("[](" * 2000 + "x" * 2000 + ")" * 2000)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 2.0, "ReDoS or excessive backtracking suspected")

    def test_malformed_unclosed_markdown(self):
        cases = [
            "**bold no close",
            "```\ncode no close",
            "*italic",
            "`code",
            "___under",
            "[unclosed link](url",
            "![unclosed img](src",
        ]
        for s in cases:
            r = MarkdownRenderer.render(s)
            self.assertIsInstance(r, str)
            self.assertNotIn("<script>", r)

    def test_very_long_input(self):
        big = "x" * (1024 * 1024)
        r = MarkdownRenderer.render(big)
        self.assertIsInstance(r, str)
        self.assertIn("x", r)

    def test_unicode_and_control_chars(self):
        cases = [
            "\x00hello",
            "hello\x07world",
            "\u202eRTL",
            "\ufffd replacement",
            "# header \n normal",
        ]
        for s in cases:
            r = MarkdownRenderer.render(s)
            self.assertIsInstance(r, str)

    def test_render_returns_string(self):
        r = MarkdownRenderer.render("Hello **world**")
        self.assertIsInstance(r, str)
        self.assertIn("Hello", r)
        self.assertIn("strong", r)

    def test_message_content_style_input_safe(self):
        """Simulate message body (e.g. decoded from LXMF) passed to render; must not crash or emit script."""
        cases = [
            b"Hello world".decode("utf-8"),
            ("Hi \ufffd replacement char " * 10).strip(),
            "\x00\x01\n\t\r",
            "<script>alert(1)</script> normal text",
            "**bold** and [link](javascript:x) end",
            "\u202eRTL override",
        ]
        for s in cases:
            r = MarkdownRenderer.render(s)
            self.assertIsInstance(r, str)
            self.assertNotIn("<script>", r)
            self.assertNotIn("javascript:", r)
