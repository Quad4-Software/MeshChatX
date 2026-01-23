import { describe, it, expect, beforeEach } from "vitest";
import MicronParser from "@/js/MicronParser";

describe("MicronParser.js", () => {
    let parser;

    beforeEach(() => {
        parser = new MicronParser(true, false); // darkTheme = true, enableForceMonospace = false
    });

    describe("formatNomadnetworkUrl", () => {
        it("formats nomadnetwork URL correctly", () => {
            expect(MicronParser.formatNomadnetworkUrl("example.com")).toBe("nomadnetwork://example.com");
        });
    });

    describe("convertMicronToHtml", () => {
        it("converts simple text to HTML", () => {
            const markup = "Hello World";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("Hello World");
            expect(html).toContain("<div");
        });

        it("converts headings correctly", () => {
            const markup = "> Heading 1\n>> Heading 2";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("Heading 1");
            expect(html).toContain("Heading 2");
            // Check for styles applied to headings (in dark theme)
            expect(html).toContain("background-color: rgb(187, 187, 187)"); // #bbb
            expect(html).toContain("background-color: rgb(153, 153, 153)"); // #999
        });

        it("converts horizontal dividers", () => {
            const markup = "-";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("<hr");
        });

        it("handles bold formatting", () => {
            const markup = "`!Bold Text`!";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("font-weight: bold");
            expect(html).toContain("Bold Text");
        });

        it("handles italic formatting", () => {
            const markup = "`*Italic Text`*";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("font-style: italic");
            expect(html).toContain("Italic Text");
        });

        it("handles underline formatting", () => {
            const markup = "`_Underlined Text`_";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("text-decoration: underline");
            expect(html).toContain("Underlined Text");
        });

        it("handles combined formatting", () => {
            const markup = "`!`_Bold Underlined Text`_`!";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("font-weight: bold");
            expect(html).toContain("text-decoration: underline");
            expect(html).toContain("Bold Underlined Text");
        });

        it("handles literal mode", () => {
            const markup = "`=\n`*Not Italic`*\n`=";
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toContain("font-style: italic");
            expect(html).toContain("`*Not Italic`*");
        });

        it("handles links correctly", () => {
            const markup = "`[Label`example.com]";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("<a");
            expect(html).toContain('href="nomadnetwork://example.com"');
            expect(html).toContain("Label");
        });

        it("handles input fields", () => {
            const markup = "`<24|field_name`Initial Value>";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("<input");
            expect(html).toContain('name="field_name"');
            expect(html).toContain('value="Initial Value"');
        });

        it("handles checkboxes", () => {
            const markup = "`<?|checkbox_name|val|*`Checkbox Label>";
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain('type="checkbox"');
            expect(html).toContain('name="checkbox_name"');
            expect(html).toContain('value="val"');
            expect(html).toContain("Checkbox Label");
        });
    });

    describe("colorToCss", () => {
        it("expands 3-digit hex", () => {
            expect(parser.colorToCss("abc")).toBe("#abc");
        });

        it("returns 6-digit hex", () => {
            expect(parser.colorToCss("abcdef")).toBe("#abcdef");
        });

        it("handles grayscale format", () => {
            expect(parser.colorToCss("g50")).toBe("#7f7f7f"); // 50 * 2.55 = 127.5 -> 7f
        });

        it("returns null for unknown formats", () => {
            expect(parser.colorToCss("invalid")).toBeNull();
        });
    });
});
