import { describe, it, expect } from "vitest";
import MarkdownRenderer from "@/js/MarkdownRenderer";

describe("MarkdownRenderer.js", () => {
    describe("render (ConversationViewer / message bodies)", () => {
        it("escapes leading greater-than so blockquote regex does not apply (documented behaviour)", () => {
            const result = MarkdownRenderer.render("> quoted line\n\nNormal paragraph.");
            expect(result).toContain("&gt; quoted line");
            expect(result).toContain("Normal paragraph");
            expect(result).not.toContain("blockquote");
        });
    });

    describe("render", () => {
        it("renders basic text correctly", () => {
            expect(MarkdownRenderer.render("Hello")).toContain("Hello");
        });

        it("renders bold text correctly", () => {
            const result = MarkdownRenderer.render("**Bold**");
            expect(result).toContain("<strong>Bold</strong>");
        });

        it("renders italic text correctly", () => {
            const result = MarkdownRenderer.render("*Italic*");
            expect(result).toContain("<em>Italic</em>");
        });

        it("renders underscore italic when delimiters are word boundaries", () => {
            const result = MarkdownRenderer.render("this is _italic_ text");
            expect(result).toContain("this is <em>italic</em> text");
        });

        it("renders bold and italic text correctly", () => {
            const result = MarkdownRenderer.render("***Bold and Italic***");
            expect(result).toContain("<strong><em>Bold and Italic</em></strong>");
        });

        it("renders headers correctly", () => {
            expect(MarkdownRenderer.render("# Header 1")).toContain("<h1");
            expect(MarkdownRenderer.render("## Header 2")).toContain("<h2");
            expect(MarkdownRenderer.render("### Header 3")).toContain("<h3");
        });

        it("renders inline code correctly", () => {
            const result = MarkdownRenderer.render("`code`");
            expect(result).toContain("<code");
            expect(result).toContain("code");
        });

        it("keeps underscores intact in long https links", () => {
            const url = "https://git.quad4.io/RNS-Things/MeshChatX/src/branch/dev/docs/meshchatx_on_raspberry_pi.md";
            const result = MarkdownRenderer.render(`visit ${url}`);
            expect(result).toContain(`href="${url}"`);
            expect(result).toContain(url);
            expect(result).not.toContain("<em>on</em>");
            expect(result).not.toContain("<em>raspberry</em>");
        });

        it("renders fenced code blocks correctly", () => {
            const result = MarkdownRenderer.render("```python\nprint('hello')\n```");
            expect(result).toContain("<pre");
            expect(result).toContain("<code");
            expect(result).toContain("language-python");
            expect(result).toContain("print(&#039;hello&#039;)");
        });

        it("handles paragraphs correctly", () => {
            const result = MarkdownRenderer.render("Para 1\n\nPara 2");
            expect(result).toContain("<p");
            expect(result).toContain("Para 1");
            expect(result).toContain("Para 2");
        });

        it("does not treat intraword underscores as italic markdown", () => {
            const result = MarkdownRenderer.render("snake_case_identifier should remain plain");
            expect(result).toContain("snake_case_identifier should remain plain");
            expect(result).not.toContain("<em>case</em>");
        });

        it("keeps underscore-heavy urls intact while still rendering links", () => {
            const url =
                "https://example.com/docs/meshchatx_on_raspberry_pi.md?file=meshchatx_on_raspberry_pi.md#meshchatx_on_raspberry_pi";
            const result = MarkdownRenderer.render(`see ${url} now`);
            expect(result).toContain(`href="${url}"`);
            expect(result).toContain(url);
            expect(result).not.toContain("<em>on</em>");
            expect(result).not.toContain("<em>raspberry</em>");
        });

        it("renders multiple urls in one line without corruption", () => {
            const a = "https://example.com/docs/meshchatx_on_pi.md";
            const b = "https://example.com/plain";
            const result = MarkdownRenderer.render(`links: ${a} and ${b}`);
            expect(result).toContain(`href="${a}"`);
            expect(result).toContain(`href="${b}"`);
            expect((result.match(/<a href=/g) || []).length).toBe(2);
        });

        it("trims trailing punctuation around links while keeping display punctuation", () => {
            const result = MarkdownRenderer.render("Check (https://example.com/path_(v1)), and continue.");
            expect(result).toContain('href="https://example.com/path_(v1)"');
            expect(result).toContain("</a>), and continue.");
        });

        it("supports encoded chars and balanced parentheses in link path", () => {
            const url = "https://example.com/docs/file%5Fname_(v1).md";
            const result = MarkdownRenderer.render(`open ${url}`);
            expect(result).toContain(`href="${url}"`);
        });

        it("keeps escaped entities in query string links", () => {
            const url = "https://example.com/search?q=a&amp;lang=en";
            const result = MarkdownRenderer.render(`lookup ${url}`);
            expect(result).toContain('href="https://example.com/search?q=a&amp;amp;lang=en"');
            expect(result).toContain("https://example.com/search?q=a&amp;amp;lang=en");
        });

        it("handles links at line boundaries with newline conversion", () => {
            const url = "https://example.com/meshchatx_on_pi.md";
            const result = MarkdownRenderer.render(`${url}\nnext line`);
            expect(result).toContain(`href="${url}"`);
            expect(result).toContain("<br>next line");
        });

        it("mixes underscore markdown with underscore urls safely", () => {
            const url = "https://example.com/meshchatx_on_raspberry_pi.md";
            const result = MarkdownRenderer.render(`_label_ ${url} _tail_`);
            expect(result).toContain("<em>label</em>");
            expect(result).toContain("<em>tail</em>");
            expect(result).toContain(`href="${url}"`);
            expect(result).not.toContain("<em>on</em>");
        });

        it("escapes pre-rendered html input safely instead of nesting raw anchors", () => {
            const preRendered = '<p><a href="https://example.com/path_(v1)">https://example.com/path_(v1)</a></p>';
            const result = MarkdownRenderer.render(preRendered);
            expect(result).toContain("&lt;p&gt;");
            expect(result).toContain("&lt;a href=&quot;");
            expect(result).not.toContain("<script");
        });
    });

    describe("security: XSS prevention", () => {
        it("escapes script tags", () => {
            const malformed = "<script>alert('xss')</script>";
            const result = MarkdownRenderer.render(malformed);
            expect(result).not.toContain("<script>");
            expect(result).toContain("&lt;script&gt;");
        });

        it("escapes onerror attributes in images", () => {
            const malformed = '<img src="x" onerror="alert(1)">';
            const result = MarkdownRenderer.render(malformed);
            expect(result).not.toContain("<img");
            expect(result).toContain("&lt;img");
            expect(result).toContain("onerror=&quot;alert(1)&quot;");
        });

        it("escapes html in code blocks", () => {
            const malformed = "```\n<script>alert(1)</script>\n```";
            const result = MarkdownRenderer.render(malformed);
            expect(result).toContain("&lt;script&gt;");
        });

        it("escapes html in inline code", () => {
            const malformed = "`<script>alert(1)</script>`";
            const result = MarkdownRenderer.render(malformed);
            expect(result).toContain("&lt;script&gt;");
        });
    });

    describe("reticulum links", () => {
        it("detects nomadnet:// links with hash and path", () => {
            const text = "check this out: nomadnet://1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu";
            const result = MarkdownRenderer.render(text);
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
            expect(result).toContain("nomadnet://1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu");
        });

        it("detects bare hash and path links as nomadnet", () => {
            const text = "node is at 1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu";
            const result = MarkdownRenderer.render(text);
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
            expect(result).toContain("1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu");
        });

        it("detects nomadnet:// links with just hash", () => {
            const text = "nomadnet://1dfeb0d794963579bd21ac8f153c77a4";
            const result = MarkdownRenderer.render(text);
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
        });

        it("detects bare hash as lxmf link", () => {
            const text = "send to 1dfeb0d794963579bd21ac8f153c77a4";
            const result = MarkdownRenderer.render(text);
            expect(result).toContain('class="lxmf-link');
            expect(result).toContain('data-lxmf-address="1dfeb0d794963579bd21ac8f153c77a4"');
        });

        it("does not detect invalid hashes", () => {
            const text = "not-a-hash:/page/index.mu";
            const result = MarkdownRenderer.render(text);
            expect(result).not.toContain("nomadnet-link");
            expect(result).not.toContain("lxmf-link");
        });
    });

    describe("fuzzing: stability testing", () => {
        const generateRandomString = (length) => {
            const chars =
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;':\",./<>?`~ \n\r\t";
            let result = "";
            for (let i = 0; i < length; i++) {
                result += chars.charAt(Math.floor(Math.random() * chars.length));
            }
            return result;
        };

        it("handles random inputs without crashing (100 iterations)", () => {
            for (let i = 0; i < 100; i++) {
                const randomText = generateRandomString(Math.floor(Math.random() * 1000));
                expect(() => {
                    MarkdownRenderer.render(randomText);
                }).not.toThrow();
            }
        });

        it("handles deeply nested or complex markdown patterns without crashing", () => {
            const complex = "# ".repeat(100) + "**".repeat(100) + "```".repeat(100) + "```\n".repeat(10);
            expect(() => {
                MarkdownRenderer.render(complex);
            }).not.toThrow();
        });

        it("handles large inputs correctly (1MB of random text)", () => {
            const largeText = generateRandomString(1024 * 1024);
            const start = Date.now();
            const result = MarkdownRenderer.render(largeText);
            const end = Date.now();

            expect(typeof result).toBe("string");
            // performance check: should be relatively fast (less than 500ms for 1MB usually)
            expect(end - start).toBeLessThan(1000);
        });

        it("handles potential ReDoS patterns (repeated separators)", () => {
            // Test patterns that often cause ReDoS in poorly written markdown parsers (can never be too careful, especially on public testnets)
            const redosPatterns = [
                "*".repeat(10000), // Long string of bold markers
                "#".repeat(10000), // Long string of header markers
                "`".repeat(10000), // Long string of backticks
                " ".repeat(10000) + "\n", // Long string of whitespace
                "[](".repeat(5000), // Unclosed links (if we added them)
                "** ".repeat(5000), // Bold marker followed by space repeated
            ];

            redosPatterns.forEach((pattern) => {
                const start = Date.now();
                MarkdownRenderer.render(pattern);
                const end = Date.now();
                expect(end - start).toBeLessThan(100); // Should be very fast
            });
        });

        it("handles unicode homoglyphs and special characters without interference", () => {
            const homoglyphs = [
                "**bold**",
                "∗∗notbold∗∗", // unicode asterisks
                "# header",
                "＃ not header", // fullwidth hash
                "`code`",
                "｀notcode｀", // fullwidth backtick
            ];
            homoglyphs.forEach((text) => {
                const result = MarkdownRenderer.render(text);
                expect(typeof result).toBe("string");
            });
        });

        it("fuzzing: full unicode code points do not crash render or strip", () => {
            for (let i = 0; i < 200; i++) {
                let s = "";
                const len = Math.floor(Math.random() * 900);
                for (let j = 0; j < len; j++) {
                    s += String.fromCharCode(Math.floor(Math.random() * 65536));
                }
                expect(() => MarkdownRenderer.render(s)).not.toThrow();
                expect(() => MarkdownRenderer.strip(s)).not.toThrow();
                const r = MarkdownRenderer.render(s);
                expect(r.toLowerCase()).not.toContain("<script");
            }
        });

        it("handles malformed or unclosed markdown tags gracefully", () => {
            const malformed = [
                "**bold",
                "```python\nprint(1)",
                "#header", // no space
                "`code",
                "___triple",
                "**bold*italic**",
                "***bolditalic**",
            ];
            malformed.forEach((text) => {
                expect(() => MarkdownRenderer.render(text)).not.toThrow();
            });
        });

        it("underscore-heavy fuzz input does not create unbalanced emphasis tags", () => {
            const randomUnderscoreText = () => {
                const parts = [
                    "_",
                    "__",
                    "___",
                    "snake_case",
                    "meshchatx_on_pi",
                    " ",
                    "text",
                    "https://example.com/meshchatx_on_pi.md",
                ];
                let out = "";
                for (let i = 0; i < 200; i++) {
                    out += parts[Math.floor(Math.random() * parts.length)];
                }
                return out;
            };
            for (let i = 0; i < 50; i++) {
                const rendered = MarkdownRenderer.render(randomUnderscoreText());
                const opensEm = (rendered.match(/<em>/g) || []).length;
                const closesEm = (rendered.match(/<\/em>/g) || []).length;
                const opensStrong = (rendered.match(/<strong>/g) || []).length;
                const closesStrong = (rendered.match(/<\/strong>/g) || []).length;
                expect(opensEm).toBe(closesEm);
                expect(opensStrong).toBe(closesStrong);
            }
        });
    });

    describe("isSingleEmojiMessage", () => {
        it("is true for one emoji and false for text or multiple emojis", () => {
            expect(MarkdownRenderer.isSingleEmojiMessage("\u{1F600}")).toBe(true);
            expect(MarkdownRenderer.isSingleEmojiMessage("  \u{1F600}  ")).toBe(true);
            expect(MarkdownRenderer.isSingleEmojiMessage("**\u{1F600}**")).toBe(true);
            expect(MarkdownRenderer.isSingleEmojiMessage("\u{1F600}\u{1F600}")).toBe(false);
            expect(MarkdownRenderer.isSingleEmojiMessage("hi")).toBe(false);
            expect(MarkdownRenderer.isSingleEmojiMessage("\u{1F600} a")).toBe(false);
        });

        it("treats ZWJ family and skin tone as a single emoji", () => {
            expect(MarkdownRenderer.isSingleEmojiMessage("\u{1F468}\u{200D}\u{1F469}\u{200D}\u{1F467}")).toBe(true);
            expect(MarkdownRenderer.isSingleEmojiMessage("\u{1F44D}\u{1F3FD}")).toBe(true);
        });
    });

    describe("strip", () => {
        it("strips markdown correctly", () => {
            const md = "# Header\n**Bold** *Italic* `code` ```\nblock\n```";
            const stripped = MarkdownRenderer.strip(md);
            expect(stripped).toContain("Header");
            expect(stripped).toContain("Bold");
            expect(stripped).toContain("Italic");
            expect(stripped).toContain("code");
            expect(stripped).toContain("[Code Block]");
            expect(stripped).not.toContain("# ");
            expect(stripped).not.toContain("**");
            expect(stripped).not.toContain("` ");
        });

        it("strip removes underscore italics but keeps intraword underscores", () => {
            const input = "before _italic_ after and snake_case_word";
            const stripped = MarkdownRenderer.strip(input);
            expect(stripped).toContain("before italic after");
            expect(stripped).toContain("snake_case_word");
            expect(stripped).not.toContain("_italic_");
        });

        it("strip handles null and undefined without throwing", () => {
            expect(MarkdownRenderer.strip(null)).toBe("");
            expect(MarkdownRenderer.strip(undefined)).toBe("");
        });

        it("strip handles ReDoS-prone patterns without hanging", () => {
            const start = Date.now();
            MarkdownRenderer.strip("*".repeat(5000));
            MarkdownRenderer.strip("`".repeat(5000));
            MarkdownRenderer.strip("# ".repeat(2000));
            expect(Date.now() - start).toBeLessThan(200);
        });

        it("strip keeps intraword underscores intact", () => {
            const url = "https://git.quad4.io/RNS-Things/MeshChatX/src/branch/dev/docs/meshchatx_on_raspberry_pi.md";
            expect(MarkdownRenderer.strip(url)).toBe(url);
        });

        it("strip returns string for malformed and edge input", () => {
            const edge = ["**no close", "```\ncode", "", "   ", "\n\n", "[[CB0]] literal"];
            edge.forEach((s) => {
                const out = MarkdownRenderer.strip(s);
                expect(typeof out).toBe("string");
            });
        });
    });

    describe("edge: non-string and invalid input", () => {
        it("render does not throw on null or undefined", () => {
            expect(MarkdownRenderer.render(null)).toBe("");
            expect(MarkdownRenderer.render(undefined)).toBe("");
        });

        it("render returns string for number input (coerced)", () => {
            const r = MarkdownRenderer.render(12345);
            expect(typeof r).toBe("string");
            expect(r).toContain("12345");
        });

        it("render never returns executable script for any input", () => {
            const risky = [
                "<script>alert(1)</script>",
                "javascript:alert(1)",
                "data:text/html,<script>alert(1)</script>",
                "'';alert(1);//",
            ];
            risky.forEach((s) => {
                const r = MarkdownRenderer.render(s);
                expect(r).not.toMatch(/<script[\s>]/i);
                expect(r).not.toMatch(/\bhref\s*=\s*["']?\s*javascript:/i);
            });
        });
    });

    describe("edge: placeholder collision", () => {
        it("literal [[CB0]] in text is not treated as code block placeholder", () => {
            const text = "See [[CB0]] and [[CB1]] here.";
            const result = MarkdownRenderer.render(text);
            expect(result).toContain("[[CB0]]");
            expect(result).toContain("[[CB1]]");
        });

        it("code block renders and restores; literal [[CB0]] may be replaced when code block exists", () => {
            const text = "Before ```\na\n``` after.";
            const result = MarkdownRenderer.render(text);
            expect(result).toContain("Before");
            expect(result).toContain("after");
            expect(result).toContain("<pre");
        });
    });

    describe("message-like content (decoded LXMF body)", () => {
        it("content with null byte and control chars does not crash", () => {
            const msg = "Hello\x00world\x07\n\t";
            expect(() => MarkdownRenderer.render(msg)).not.toThrow();
            const r = MarkdownRenderer.render(msg);
            expect(typeof r).toBe("string");
            expect(r).not.toContain("<script>");
        });

        it("content with mixed unicode and markdown does not inject script", () => {
            const msg = "\u202eRTL **bold** <script>nope</script> \ufffd";
            const r = MarkdownRenderer.render(msg);
            expect(r).not.toContain("<script>");
            expect(r).toContain("&lt;script&gt;");
        });

        it("very long single-line message (100k chars) completes in reasonable time", () => {
            const msg = "x".repeat(100000);
            const start = Date.now();
            const r = MarkdownRenderer.render(msg);
            expect(Date.now() - start).toBeLessThan(500);
            expect(typeof r).toBe("string");
        });

        it("message with many newlines and markdown markers", () => {
            const msg = "# ".repeat(500) + "**".repeat(500) + "\n\n\n";
            expect(() => MarkdownRenderer.render(msg)).not.toThrow();
            const r = MarkdownRenderer.render(msg);
            expect(typeof r).toBe("string");
        });

        it("renders a real-world mixed message body safely", () => {
            const msg = [
                "# Deploy notes",
                "",
                "Read https://git.quad4.io/RNS-Things/MeshChatX/src/branch/dev/docs/meshchatx_on_raspberry_pi.md, then ping",
                "nomadnet://1dfeb0d794963579bd21ac8f153c77a4:/page/meshchatx_on_pi.mu",
                "",
                "`inline_code` and _italic_ and snake_case stay sane.",
                "",
                "```txt",
                "https://example.com/not_linked_inside_code",
                "```",
            ].join("\n");
            const result = MarkdownRenderer.render(msg);
            expect(result).toContain("<h1");
            expect(result).toContain(
                'href="https://git.quad4.io/RNS-Things/MeshChatX/src/branch/dev/docs/meshchatx_on_raspberry_pi.md"'
            );
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/meshchatx_on_pi.mu"');
            expect(result).toContain("<code");
            expect(result).toContain("<pre");
            expect(result).not.toContain("<em>case</em>");
        });
    });
});
