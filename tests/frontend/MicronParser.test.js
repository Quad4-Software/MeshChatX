import { describe, it, expect, beforeEach } from "vitest";
import MicronParser from "@/js/MicronParser";

describe("MicronParser.js", () => {
    let parser;

    beforeEach(() => {
        parser = new MicronParser(true, false); // darkTheme = true, enableForceMonospace = false
    });

    describe("PARTIAL_LINE_REGEX", () => {
        it("matches partial without refresh", () => {
            const m = "`{f64a846313b874ee4a357040807f8c77:/page/partial.mu}"
                .trim()
                .match(MicronParser.PARTIAL_LINE_REGEX);
            expect(m).not.toBeNull();
            expect(m[1]).toBe("f64a846313b874ee4a357040807f8c77");
            expect(m[2]).toBe("/page/partial.mu");
            expect(m[3]).toBeUndefined();
        });

        it("matches partial with refresh", () => {
            const m = "`{f64a846313b874ee4a357040807f8c77:/page/ref.mu`30}"
                .trim()
                .match(MicronParser.PARTIAL_LINE_REGEX);
            expect(m).not.toBeNull();
            expect(m[3]).toBe("30");
        });

        it("does not match without leading backtick", () => {
            expect("{f64a846313b874ee4a357040807f8c77:/page/x.mu}".match(MicronParser.PARTIAL_LINE_REGEX)).toBeNull();
        });

        it("does not match short hash", () => {
            expect("`{f64a846313b874ee4a35704:/page/x.mu}".match(MicronParser.PARTIAL_LINE_REGEX)).toBeNull();
        });
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

        describe("partials", () => {
            it("emits placeholder for partial line without refresh", () => {
                const dest = "f64a846313b874ee4a357040807f8c77";
                const path = "/page/partial_1.mu";
                const markup = "`{" + dest + ":" + path + "}";
                const html = parser.convertMicronToHtml(markup);
                expect(html).toContain('class="mu-partial"');
                expect(html).toContain('data-partial-id="partial-0"');
                expect(html).toContain('data-dest="' + dest + '"');
                expect(html).toContain('data-path="' + path + '"');
                expect(html).not.toContain("data-refresh");
                expect(html).toContain("Loading...");
            });

            it("emits placeholder for partial line with refresh seconds", () => {
                const dest = "f64a846313b874ee4a357040807f8c77";
                const path = "/page/refreshing_partial.mu";
                const markup = "`{" + dest + ":" + path + "`10}";
                const html = parser.convertMicronToHtml(markup);
                expect(html).toContain('class="mu-partial"');
                expect(html).toContain('data-partial-id="partial-0"');
                expect(html).toContain('data-dest="' + dest + '"');
                expect(html).toContain('data-path="' + path + '"');
                expect(html).toContain('data-refresh="10"');
                expect(html).toContain("Loading...");
            });

            it("injects partialContents when provided", () => {
                const dest = "a".repeat(32);
                const path = "/page/partial.mu";
                const markup = "`{" + dest + ":" + path + "}";
                const injected = "<span>Injected partial content</span>";
                const html = parser.convertMicronToHtml(markup, { "partial-0": injected });
                expect(html).toContain(injected);
                expect(html).not.toContain("Loading...");
                expect(html).not.toContain("mu-partial");
            });

            it("assigns unique partial ids for multiple partials", () => {
                const dest = "b".repeat(32);
                const markup = "`{" + dest + ":/page/a.mu}\n`{" + dest + ":/page/b.mu}";
                const html = parser.convertMicronToHtml(markup);
                expect(html).toContain('data-partial-id="partial-0"');
                expect(html).toContain('data-partial-id="partial-1"');
                expect(html).toContain('data-path="/page/a.mu"');
                expect(html).toContain('data-path="/page/b.mu"');
            });

            it("does not interpret partial syntax inside literal block", () => {
                const dest = "c".repeat(32);
                const markup = "`=\n`{" + dest + ":/page/partial.mu}\n`=";
                const html = parser.convertMicronToHtml(markup);
                expect(html).not.toContain("mu-partial");
                expect(html).toContain("`{" + dest + ":/page/partial.mu}");
            });

            it("does not treat similar-looking line as partial without backtick", () => {
                const markup = "{f64a846313b874ee4a357040807f8c77:/page/partial.mu}";
                const html = parser.convertMicronToHtml(markup);
                expect(html).not.toContain("mu-partial");
            });
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

    describe("risky: XSS and injection", () => {
        it("output contains no raw script tag for script-like markup", () => {
            const markup = "<script>alert(1)</script> hello";
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<script[\s>]/i);
        });

        it("output contains no javascript: in href for link-like markup", () => {
            const markup = "`[click`javascript:alert(1)]";
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/\bhref\s*=\s*["']?\s*javascript:/i);
        });

        it("output contains no data: html in href", () => {
            const markup = "`[x`data:text/html,<script>alert(1)</script>]";
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/\bhref\s*=\s*["']?\s*data\s*:\s*text\/html/i);
        });

        it("does not produce executable event handler attributes", () => {
            const markup = '<span onclick="alert(1)">x</span>';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<[^>]*\bonclick\s*=\s*["']?\s*alert/i);
        });
    });

    describe("risky: stability and edge input", () => {
        it("does not throw on null or undefined markup", () => {
            expect(() => parser.convertMicronToHtml(null)).not.toThrow();
            expect(() => parser.convertMicronToHtml(undefined)).not.toThrow();
        });

        it("handles very long input without hanging", () => {
            const long = "> ".repeat(5000) + "x";
            const start = Date.now();
            const html = parser.convertMicronToHtml(long);
            expect(Date.now() - start).toBeLessThan(500);
            expect(typeof html).toBe("string");
        });

        it("handles repeated backticks (ReDoS-prone pattern) quickly", () => {
            const markup = "`".repeat(3000);
            const start = Date.now();
            parser.convertMicronToHtml(markup);
            expect(Date.now() - start).toBeLessThan(200);
        });

        it("handles control chars and null byte", () => {
            const markup = "hello\x00world\x07\n\t";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
        });

        it("handles unicode and RTL override", () => {
            const markup = "\u202eRTL `!bold`! text \ufffd";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
            expect(html).not.toMatch(/<script[\s>]/i);
        });
    });
});
