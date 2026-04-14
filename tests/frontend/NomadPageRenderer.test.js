import { describe, expect, it } from "vitest";
import MicronParser from "../../meshchatx/src/frontend/js/MicronParser";
import {
    escapeNomadPlainText,
    renderNomadHtmlPage,
    renderNomadMarkdown,
    renderNomadPageByPath,
    sanitizeNomadHtmlFragment,
} from "../../meshchatx/src/frontend/js/NomadPageRenderer";

describe("NomadPageRenderer", () => {
    it("renders markdown to safe HTML without script tags", () => {
        const html = renderNomadMarkdown("# Title\n\n[x](javascript:alert(1))");
        expect(html).toContain("Title");
        expect(html.toLowerCase()).not.toContain("<script");
        expect(html).not.toContain("javascript:");
    });

    it("normalizes ATX headings when space is missing after hashes", () => {
        const html = renderNomadMarkdown("#Hello\n\n##There\n\n####Deep");
        expect(html).toContain("<h1");
        expect(html).toContain("Hello");
        expect(html).toContain("<h2");
        expect(html).toContain("<h4");
    });

    it("wraps markdown in nomad-markdown container", () => {
        const html = renderNomadMarkdown("x");
        expect(html).toContain('class="nomad-markdown"');
    });

    it("strips external http links from markdown output", () => {
        const html = renderNomadMarkdown("[a](https://evil.example/)");
        expect(html).not.toContain("evil.example");
    });

    it("allows nomad-style href on links after sanitization", () => {
        const html = renderNomadMarkdown("[local](:page/other.mu)");
        expect(html).toContain(":page/other.mu");
    });

    it("sanitizes HTML documents and removes script", () => {
        const html = renderNomadHtmlPage(
            "<!DOCTYPE html><html><head><style>body{color:red}</style></head><body><p>Hi</p><script>x</script></body></html>"
        );
        expect(html.toLowerCase()).not.toContain("<script");
        expect(html).toContain("Hi");
        expect(html).toContain("nomad-html-root");
        expect(html).toContain(".nomad-html-root");
        expect(html).toContain("color:red");
    });

    it("removes iframe and external stylesheet references from HTML", () => {
        const html = renderNomadHtmlPage(
            '<html><head><link rel="stylesheet" href="https://evil.example/s.css"/></head><body><iframe src="https://x"></iframe><p>x</p></body></html>'
        );
        expect(html.toLowerCase()).not.toContain("iframe");
        expect(html).not.toContain("evil.example");
    });

    it("escapes plain text pages", () => {
        const out = escapeNomadPlainText("<script>bad</script>");
        expect(out).not.toContain("<script>");
        expect(out).toContain("&lt;script&gt;");
    });

    it("renderNomadPageByPath picks format by extension", () => {
        const dest = "a".repeat(32);
        const muHtml = renderNomadPageByPath(`${dest}:/page/x.mu`, "Hello mesh", {}, MicronParser);
        expect(typeof muHtml).toBe("string");
        expect(muHtml.length).toBeGreaterThan(0);
        expect(renderNomadPageByPath("/page/a.md", "# T", {}, MicronParser)).toContain("T");
        expect(renderNomadPageByPath("/page/a.txt", "a<b>", {}, MicronParser)).toContain("&lt;");
        expect(renderNomadPageByPath("/page/a.html", '<p class="x">z</p>', {}, MicronParser)).toContain("z");
    });

    it("sanitizeNomadHtmlFragment handles arbitrary strings without throwing", () => {
        expect(() => sanitizeNomadHtmlFragment("<div>ok</div>")).not.toThrow();
    });

    it("fuzzing: handles random strings in markdown and HTML sanitization", () => {
        for (let i = 0; i < 200; i++) {
            let s = "";
            const len = Math.floor(Math.random() * 800);
            for (let j = 0; j < len; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 65536));
            }
            expect(() => renderNomadMarkdown(s)).not.toThrow();
            expect(() => sanitizeNomadHtmlFragment(s)).not.toThrow();
            expect(() => renderNomadHtmlPage(s)).not.toThrow();
        }
    });
});
