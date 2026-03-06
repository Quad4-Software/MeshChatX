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

    describe("adversarial: deeply nested tags", () => {
        it("handles 500 levels of nested bold without stack overflow", () => {
            const open = "`!".repeat(500);
            const close = "`!".repeat(500);
            const markup = open + "deep" + close;
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
            expect(html).toContain("deep");
        });

        it("handles 500 levels of mixed nesting (bold+italic+underline)", () => {
            const tags = ["`!", "`*", "`_"];
            let markup = "";
            for (let i = 0; i < 500; i++) markup += tags[i % 3];
            markup += "payload";
            for (let i = 499; i >= 0; i--) markup += tags[i % 3];
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
            const html = parser.convertMicronToHtml(markup);
            expect(html).toContain("payload");
        });

        it("handles deeply nested headings", () => {
            const markup = Array.from({ length: 200 }, (_, i) => ">".repeat(i + 1) + " H").join("\n");
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });
    });

    describe("adversarial: unclosed and mismatched tags", () => {
        it("handles unclosed bold tag", () => {
            const markup = "`!unclosed bold without end";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
            expect(html).not.toMatch(/<script[\s>]/i);
        });

        it("handles unclosed italic tag", () => {
            const markup = "`*unclosed italic";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
        });

        it("handles mismatched open/close order", () => {
            const markup = "`!`*bold-italic`!`*";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
        });

        it("handles unclosed link", () => {
            const markup = "`[link text without closing";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
            expect(html).not.toMatch(/\bhref\s*=\s*["']?\s*javascript:/i);
        });

        it("handles unclosed input", () => {
            const markup = "`<24|field_name`value without closing";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
        });

        it("handles unclosed literal mode", () => {
            const markup = "`=\nsome literal text that never closes";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
        });
    });

    describe("adversarial: malformed UTF-8 and encoding attacks", () => {
        it("handles UTF-8 overlong encoding sequences", () => {
            const markup = "test\xC0\xAFpath\xE0\x80\xAFmore";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });

        it("handles surrogate halves", () => {
            const markup = "text\uD800alone\uDC00orphan";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });

        it("handles BOM characters", () => {
            const markup = "\uFEFF> Heading with BOM";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
        });

        it("handles zero-width joiner/non-joiner", () => {
            const markup = "`!\u200Bbold\u200Dtext`!";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
        });

        it("handles full-width characters in tag positions", () => {
            const markup = "\uFF40\uFF01fullwidth backtick-bang\uFF40\uFF01";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });
    });

    describe("adversarial: null bytes and control characters", () => {
        it("handles null bytes between tag markers", () => {
            const markup = "`\x00!bold\x00`!";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });

        it("handles line of only null bytes", () => {
            const markup = "\x00".repeat(100);
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });

        it("handles ASCII control characters 0x01-0x1F", () => {
            let markup = "";
            for (let i = 1; i < 32; i++) markup += String.fromCharCode(i);
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<script[\s>]/i);
        });

        it("handles escape sequences in links", () => {
            const markup = "`[label`\x1B[31mred\x1B[0m]";
            const html = parser.convertMicronToHtml(markup);
            expect(typeof html).toBe("string");
        });

        it("handles DEL character (0x7F)", () => {
            const markup = "hello\x7Fworld";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });
    });

    describe("adversarial: ReDoS patterns", () => {
        it("handles alternating backtick-bracket pattern quickly", () => {
            const markup = "`[".repeat(1000) + "x" + "]".repeat(1000);
            const start = Date.now();
            parser.convertMicronToHtml(markup);
            expect(Date.now() - start).toBeLessThan(500);
        });

        it("handles alternating backtick-angle pattern quickly", () => {
            const markup = "`<".repeat(1000) + "y" + ">".repeat(1000);
            const start = Date.now();
            parser.convertMicronToHtml(markup);
            expect(Date.now() - start).toBeLessThan(500);
        });

        it("handles pathological color code pattern quickly", () => {
            const markup = "`Fabc".repeat(500);
            const start = Date.now();
            parser.convertMicronToHtml(markup);
            expect(Date.now() - start).toBeLessThan(500);
        });

        it("handles massive number of newlines quickly", () => {
            const markup = "\n".repeat(10000);
            const start = Date.now();
            parser.convertMicronToHtml(markup);
            expect(Date.now() - start).toBeLessThan(500);
        });

        it("handles rapid format toggle (open/close/open/close) quickly", () => {
            const markup = "`!x`!".repeat(2000);
            const start = Date.now();
            parser.convertMicronToHtml(markup);
            expect(Date.now() - start).toBeLessThan(500);
        });
    });

    describe("adversarial: XSS bypass attempts", () => {
        it("blocks SVG onload XSS", () => {
            const markup = '<svg onload="alert(1)">';
            const html = parser.convertMicronToHtml(markup);
            const div = document.createElement("div");
            div.innerHTML = html;
            const svgs = div.querySelectorAll("svg");
            for (const svg of svgs) {
                expect(svg.getAttribute("onload")).toBeNull();
            }
        });

        it("blocks img onerror XSS", () => {
            const markup = '<img src=x onerror="alert(1)">';
            const html = parser.convertMicronToHtml(markup);
            const div = document.createElement("div");
            div.innerHTML = html;
            const imgs = div.querySelectorAll("img");
            for (const img of imgs) {
                expect(img.getAttribute("onerror")).toBeNull();
            }
        });

        it("blocks iframe injection", () => {
            const markup = '<iframe src="https://evil.com"></iframe>';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<iframe[\s>]/i);
        });

        it("blocks style-based data exfiltration", () => {
            const markup = '<style>body{background:url("https://evil.com/steal")}</style>';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<style[\s>]/i);
        });

        it("blocks javascript: in link with encoding", () => {
            const markup = "`[click`java\tscript:alert(1)]";
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/\bhref\s*=\s*["']?\s*java\s*script:/i);
        });

        it("blocks vbscript: protocol", () => {
            const markup = "`[click`vbscript:MsgBox(1)]";
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/\bhref\s*=\s*["']?\s*vbscript:/i);
        });

        it("blocks meta refresh injection", () => {
            const markup = '<meta http-equiv="refresh" content="0;url=https://evil.com">';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<meta[\s>]/i);
        });

        it("blocks object/embed tags", () => {
            const markup = '<object data="evil.swf"></object><embed src="evil.swf">';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<object[\s>]/i);
            expect(html).not.toMatch(/<embed[\s>]/i);
        });

        it("blocks form action injection", () => {
            const markup = '<form action="https://evil.com"><input type="submit"></form>';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<form[\s>]/i);
        });

        it("blocks base tag hijacking", () => {
            const markup = '<base href="https://evil.com/">';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<base[\s>]/i);
        });
    });

    describe("adversarial: injection through micron features", () => {
        it("link URL with attribute injection is entity-encoded", () => {
            const markup = '`[click`" onclick="alert(1)" data-x="]';
            const html = parser.convertMicronToHtml(markup);
            const div = document.createElement("div");
            div.innerHTML = html;
            const anchors = div.querySelectorAll("a");
            for (const a of anchors) {
                expect(a.getAttribute("onclick")).toBeNull();
            }
        });

        it("input field name cannot inject HTML", () => {
            const markup = '`<24|"><script>alert(1)</script>`val>';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<script[\s>]/i);
        });

        it("checkbox value with attribute injection is entity-encoded", () => {
            const markup = '`<?|name|"><img src=x onerror=alert(1)>|`label>';
            const html = parser.convertMicronToHtml(markup);
            const div = document.createElement("div");
            div.innerHTML = html;
            const imgs = div.querySelectorAll("img");
            for (const img of imgs) {
                expect(img.getAttribute("onerror")).toBeNull();
            }
        });

        it("color code cannot inject styles or HTML", () => {
            const markup = '`F"><script>alert(1)</script>text';
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<script[\s>]/i);
        });

        it("partial hash cannot inject HTML", () => {
            const hash = 'a"><script>alert(1)</script>';
            const markup = "`{" + hash + ":/page/test.mu}";
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<script[\s>]/i);
        });
    });

    describe("adversarial: large and extreme payloads", () => {
        it("handles 100KB of plain text", () => {
            const markup = "A".repeat(100_000);
            const start = Date.now();
            const html = parser.convertMicronToHtml(markup);
            expect(Date.now() - start).toBeLessThan(2000);
            expect(typeof html).toBe("string");
        });

        it("handles 10K lines of formatted text", () => {
            const lines = Array.from({ length: 10_000 }, (_, i) => `\`!line ${i}\`!`);
            const markup = lines.join("\n");
            const start = Date.now();
            parser.convertMicronToHtml(markup);
            expect(Date.now() - start).toBeLessThan(10000);
        });

        it("handles single line of 50KB", () => {
            const markup = "`!" + "X".repeat(50_000) + "`!";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });

        it("handles empty string", () => {
            const html = parser.convertMicronToHtml("");
            expect(typeof html).toBe("string");
        });

        it("handles only whitespace", () => {
            const html = parser.convertMicronToHtml("   \t\t\n\n  ");
            expect(typeof html).toBe("string");
        });
    });

    describe("adversarial: polyglot and mixed content", () => {
        it("handles HTML/micron polyglot", () => {
            const markup = "> `!<b>Heading</b>`!\n<script>alert(1)</script>\n`[link`http://safe.com]";
            const html = parser.convertMicronToHtml(markup);
            expect(html).not.toMatch(/<script[\s>]/i);
            expect(html).toContain("Heading");
        });

        it("handles markdown-like input", () => {
            const markup = "# Not a heading\n**not bold**\n[not a link](http://evil.com)";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });

        it("handles ANSI escape codes", () => {
            const markup = "\x1B[31mred text\x1B[0m normal";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });

        it("handles mixed valid/invalid UTF-8 with micron", () => {
            const markup = "`!\uFFFD\uFFFE\uFFFF bold\uD83D\uDE00`!";
            expect(() => parser.convertMicronToHtml(markup)).not.toThrow();
        });
    });
});
