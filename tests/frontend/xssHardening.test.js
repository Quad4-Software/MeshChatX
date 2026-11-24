// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import MarkdownRenderer from "@/js/MarkdownRenderer";
import MicronParser from "@/js/MicronParser";

const HOSTILE_INPUTS = [
    '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    '<iframe src="https://evil.example"></iframe>',
    '<a href="javascript:alert(1)">x</a>',
    'javascript:alert(1)',
    'java\tscript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    'vbscript:msgbox(1)',
    '//evil.example/x',
    '"><img src=x onerror=alert(1)>',
    "'><svg onload=alert(1)>",
    "&lt;img src=x onerror=alert(1)&gt;",
];

const FORBIDDEN_TAGS = ["script", "iframe", "object", "embed", "base"];
const URL_ATTRS = ["href", "src", "srcset", "poster", "action", "formaction", "xlink:href"];
const DANGEROUS_SCHEMES = /^(javascript|vbscript|data)\s*:/i;

function assertNoExecutableMarkup(html) {
    const doc = new DOMParser().parseFromString(
        `<div id="xss-root">${html}</div>`,
        "text/html",
    );
    const root = doc.getElementById("xss-root");
    expect(root).not.toBeNull();
    for (const tag of FORBIDDEN_TAGS) {
        expect(root.querySelectorAll(tag).length, `found <${tag}>`).toBe(0);
    }
    root.querySelectorAll("*").forEach((el) => {
        for (const attr of el.attributes) {
            const name = attr.name.toLowerCase();
            expect(name, `event handler attr ${name}`).not.toMatch(/^on[a-z]/);
            if (URL_ATTRS.includes(name)) {
                const value = String(attr.value).replace(/[\u0000-\u0020]/g, "");
                expect(value, `${name}=${attr.value}`).not.toMatch(DANGEROUS_SCHEMES);
            }
            if (name === "data-http-url" || name === "data-lxmf-address") {
                const value = String(attr.value).replace(/[\u0000-\u0020]/g, "");
                expect(value, `${name}=${attr.value}`).not.toMatch(DANGEROUS_SCHEMES);
            }
        }
    });
}

describe("MarkdownRenderer XSS hardening", () => {
    for (const input of HOSTILE_INPUTS) {
        it(`escapes hostile input: ${JSON.stringify(input).slice(0, 60)}`, () => {
            const out = MarkdownRenderer.render(input);
            assertNoExecutableMarkup(out);
        });
    }

    it("does not turn markdown-style javascript links into anchors", () => {
        const out = MarkdownRenderer.render("[click](javascript:alert(1))");
        assertNoExecutableMarkup(out);
        expect(out).not.toMatch(/<a\s[^>]*href="javascript/i);
    });

    it("only auto-links http(s) URLs and keeps the real URL off href", () => {
        const out = MarkdownRenderer.render("visit https://evil.example/path now");
        expect(out).toContain('href="#"');
        expect(out).toContain('data-http-url="https://evil.example/path"');
        expect(out).not.toMatch(/href="https:\/\/evil\.example/);
    });

    it("does not auto-link non-http schemes", () => {
        for (const input of [
            "ftp://evil.example/x",
            "file:///etc/passwd",
            "mailto:a@b.c",
            "xmpp:user@evil.example",
        ]) {
            const out = MarkdownRenderer.render(input);
            expect(out).not.toContain("data-http-url");
        }
    });
});

describe("MicronParser DOMPurify sanitization", () => {
    const SANITIZE_CASES = [
        '<a href="javascript:alert(1)">x</a>',
        '<a href="java\tscript:alert(1)">x</a>',
        '<a href="java\nscript:alert(1)">x</a>',
        '<a href="&#106;avascript:alert(1)">x</a>',
        '<a href="&Tab;javascript:alert(1)">x</a>',
        '<a href="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">x</a>',
        '<a href="vbscript:msgbox(1)">x</a>',
        '<img src=x onerror=alert(1)>',
        '<svg onload=alert(1)><circle r=1></circle></svg>',
        '<a href="//evil.example/x">proto-relative</a>',
        '<base href="https://evil.example/">',
        '<form action="javascript:alert(1)"><input name=x></form>',
        '<math><mtext><table><mglyph><style><img src=x onerror=alert(1)>',
    ];

    for (const input of SANITIZE_CASES) {
        it(`sanitizes: ${JSON.stringify(input).slice(0, 60)}`, () => {
            const out = MicronParser.sanitizeRenderedMicronHtml(input);
            assertNoExecutableMarkup(out);
        });
    }

    it("keeps allowed https links and strips nothing needed", () => {
        const out = MicronParser.sanitizeRenderedMicronHtml(
            '<a href="https://example.com/path">ok</a><a href="mailto:a@b.c">mail</a>',
        );
        expect(out).toContain("https://example.com/path");
        expect(out).toContain("mailto:a@b.c");
    });
});

describe("MicronParser end-to-end hostile markup", () => {
    it("strips script and event handlers from converted micron", () => {
        const parser = new MicronParser();
        const out = parser.convertMicronToHtml(
            '<img src=x onerror=alert(1)>\n<script>alert(1)</script>\n[click](javascript:alert(1))',
        );
        assertNoExecutableMarkup(out);
    });

    it("keeps micron links on allowed schemes only", () => {
        const parser = new MicronParser();
        const out = parser.convertMicronToHtml("[docs](https://example.com/docs)");
        expect(out).not.toMatch(/href="javascript:/i);
        assertNoExecutableMarkup(out);
    });

    it("sanitizes hostile colour and font directives", () => {
        const parser = new MicronParser();
        for (const markup of [
            "#!fg=red;behavior:url(x)\nhello",
            "#!bg=blue;background-image:url(https://evil.example/x)\nhello",
            "#!font=Arial;src:url(javascript:alert(1))\nhello",
        ]) {
            const out = parser.convertMicronToHtml(markup);
            assertNoExecutableMarkup(out);
        }
    });
});
