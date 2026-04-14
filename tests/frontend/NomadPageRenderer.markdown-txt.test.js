import { describe, expect, it } from "vitest";
import MicronParser from "../../meshchatx/src/frontend/js/MicronParser";
import {
    escapeNomadPlainText,
    renderNomadMarkdown,
    renderNomadPageByPath,
} from "../../meshchatx/src/frontend/js/NomadPageRenderer";

describe("NomadPageRenderer plaintext (.txt and escapeNomadPlainText)", () => {
    it("escapes angle brackets, ampersands, and quotes", () => {
        const out = escapeNomadPlainText(`<&> "'`);
        expect(out).toContain("&lt;");
        expect(out).toContain("&gt;");
        expect(out).toContain("&amp;");
        expect(out).toContain("&quot;");
        expect(out).toContain("&#039;");
    });

    it("wraps content in a pre-wrap container class", () => {
        expect(escapeNomadPlainText("x")).toContain("whitespace-pre-wrap");
    });

    it("preserves newlines as escaped text inside the wrapper", () => {
        const out = escapeNomadPlainText("line1\nline2");
        expect(out).toContain("line1");
        expect(out).toContain("line2");
    });

    it("renderNomadPageByPath uses plaintext for .txt paths", () => {
        const html = renderNomadPageByPath("/page/readme.txt", "Plain <tag> & \" '", {}, MicronParser);
        expect(html).toContain("&lt;tag&gt;");
        expect(html).toContain("&amp;");
        expect(html).toContain("whitespace-pre-wrap");
    });

    it("renderNomadPageByPath .txt is case-insensitive on extension", () => {
        const html = renderNomadPageByPath("/page/NOTE.TXT", "ok", {}, MicronParser);
        expect(html).toContain("ok");
        expect(html).toContain("whitespace-pre-wrap");
    });

    it("empty and whitespace-only plaintext", () => {
        expect(escapeNomadPlainText("")).toContain("whitespace-pre-wrap");
        expect(escapeNomadPlainText("   \n\t  ")).toContain("whitespace-pre-wrap");
    });

    it("fuzzing: escapeNomadPlainText random unicode never throws", () => {
        for (let i = 0; i < 250; i++) {
            let s = "";
            const len = Math.floor(Math.random() * 1200);
            for (let j = 0; j < len; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 65536));
            }
            expect(() => escapeNomadPlainText(s)).not.toThrow();
            const out = escapeNomadPlainText(s);
            expect(out).not.toContain("<script");
            expect(out.toLowerCase()).not.toContain("<script");
        }
    });
});

describe("NomadPageRenderer Nomad .md pages (marked + sanitize)", () => {
    it("renders GFM-style table", () => {
        const md = ["| A | B |", "| --- | --- |", "| 1 | 2 |"].join("\n");
        const html = renderNomadMarkdown(md);
        expect(html.toLowerCase()).toContain("<table");
        expect(html).toContain("A");
        expect(html).toContain("2");
    });

    it("renders bullet and ordered list markup", () => {
        const ul = renderNomadMarkdown("- one\n- two\n");
        expect(ul.toLowerCase()).toContain("<ul");
        expect(ul).toContain("one");

        const ol = renderNomadMarkdown("1. first\n2. second\n");
        expect(ol.toLowerCase()).toContain("<ol");
        expect(ol).toContain("second");
    });

    it("renders fenced code block with language class", () => {
        const html = renderNomadMarkdown("```js\nconst x = 1;\n```");
        expect(html.toLowerCase()).toContain("<pre");
        expect(html).toContain("language-js");
        expect(html).toContain("const x");
    });

    it("renders horizontal rule", () => {
        const html = renderNomadMarkdown("before\n\n---\n\nafter");
        expect(html.toLowerCase()).toContain("<hr");
        expect(html).toContain("before");
        expect(html).toContain("after");
    });

    it("renderNomadPageByPath routes .md through markdown pipeline", () => {
        const html = renderNomadPageByPath("/page/doc.md", "## Section\n\npara", {}, MicronParser);
        expect(html).toContain("nomad-markdown");
        expect(html.toLowerCase()).toContain("<h2");
        expect(html).toContain("Section");
    });

    it("fuzzing: renderNomadMarkdown full unicode stress", () => {
        for (let i = 0; i < 200; i++) {
            let s = "";
            const len = Math.floor(Math.random() * 1000);
            for (let j = 0; j < len; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 65536));
            }
            expect(() => renderNomadMarkdown(s)).not.toThrow();
            const html = renderNomadMarkdown(s);
            expect(typeof html).toBe("string");
            expect(html.toLowerCase()).not.toContain("<script");
        }
    });
});
