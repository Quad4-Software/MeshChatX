# SPDX-License-Identifier: 0BSD
"""Adversarial link-scheme and render-safety properties for MarkdownRenderer."""

import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.markdown_renderer import MarkdownRenderer, _safe_href

# Browsers treat backslash like a forward slash inside URLs. Anything that
# normalizes to a protocol-relative or dangerous-scheme URL must be rejected.
DANGEROUS_URLS = [
    "//evil.example/x",
    "\\/evil.example/x",
    "/\\evil.example/x",
    "\\\\evil.example\\x",
    "javascript:alert(1)",
    "javAscript:alert(1)",
    "java\tscript:alert(1)",
    "java\nscript:alert(1)",
    " javascript:alert(1)",
    "data:text/html;base64,PGI+",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "JaVaScRiPt:alert(1)",
    "jav\x00ascript:alert(1)",
]

SAFE_URLS = [
    "https://example.com/a?x=1&y=2",
    "http://example.com",
    "/docs/guide",
    "#anchor",
    "mailto:user@example.com",
    "page/sibling.md",
    "a/b/c",
    "relative",
]


class TestSafeHref:
    @pytest.mark.parametrize("url", DANGEROUS_URLS)
    def test_dangerous_urls_rejected(self, url):
        assert _safe_href(url) == "#", url

    @pytest.mark.parametrize("url", SAFE_URLS)
    def test_safe_urls_pass_through(self, url):
        assert _safe_href(url) == url

    def test_rendered_link_never_contains_protocol_relative_href(self):
        for url in ("\\/evil.example/x", "/\\evil.example/x", "//evil.example/x"):
            out = MarkdownRenderer.render(f"[x]({url})")
            assert 'href="#"' in out, (url, out)
            assert "evil.example" not in out or 'href="#"' in out

    def test_rendered_link_never_contains_javascript_href(self):
        for url in ("javascript:alert(1)", "jav\tascript:alert(1)"):
            out = MarkdownRenderer.render(f"[x]({url})")
            assert 'href="javascript' not in out.lower()


class TestRenderNeverCrashes:
    @given(text=st.text(max_size=400))
    @settings(max_examples=120, deadline=5000)
    def test_arbitrary_text_never_raises(self, text):
        MarkdownRenderer.render(text)

    @given(
        body=st.text(
            alphabet="[]()!`*_~#|\\<>:/&;\"' \t\nxyz0123456789.",
            max_size=200,
        )
    )
    @settings(max_examples=200, deadline=5000)
    def test_markup_alphabet_never_raises(self, body):
        out = MarkdownRenderer.render(body)
        # Whatever comes out, an attacker cannot leave live script or
        # handler attributes behind.
        assert "<script" not in out.lower()
        assert " onerror=" not in out.lower()
        assert " onclick=" not in out.lower()
        assert "javascript:" not in out.lower()

    def test_pathological_input_bounded_time(self):
        pathological = [
            "a" * 5000 + "\n\n" + "b" * 5000,
            "[" * 2000 + "]" * 2000 + "(" * 2000 + ")" * 2000,
            "*" * 3000 + "x" + "*" * 3000,
            "|" + "-|" * 1500 + "\n" + "|" + "a|" * 1500,
            "```" * 500,
            ("- x\n" * 2000),
            ("1. y\n" * 2000),
            "![a](b)" * 1000,
            "[a](b)" * 1000,
            "_" * 4000,
            ">" * 3000,
        ]
        start = time.monotonic()
        for text in pathological:
            MarkdownRenderer.render(text)
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"render took {elapsed:.1f}s"

    def test_placeholder_names_in_user_text_do_not_break_output(self):
        # A user writing a literal placeholder must not splice code blocks.
        out = MarkdownRenderer.render("`code`\n\n[[IC0]]\n\n[[CB0]]")
        assert out.count("<code") >= 1
