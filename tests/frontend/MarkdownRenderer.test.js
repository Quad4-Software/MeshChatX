import { describe, it, expect } from "vitest";
import MarkdownRenderer from "@/js/MarkdownRenderer";

describe("MarkdownRenderer.js", () => {
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

    describe("nomadnet links", () => {
        it("detects nomadnet:// links with hash and path", () => {
            const text = "check this out: nomadnet://1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu";
            const result = MarkdownRenderer.render(text);
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
            expect(result).toContain("nomadnet://1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu");
        });

        it("detects bare hash and path links", () => {
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

        it("does not detect invalid hashes", () => {
            const text = "not-a-hash:/page/index.mu";
            const result = MarkdownRenderer.render(text);
            expect(result).not.toContain("nomadnet-link");
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
    });
});
