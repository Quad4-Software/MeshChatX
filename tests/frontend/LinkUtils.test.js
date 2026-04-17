import { describe, it, expect } from "vitest";
import LinkUtils from "@/js/LinkUtils";

describe("LinkUtils.js", () => {
    describe("renderReticulumLinks", () => {
        it("detects nomadnet:// links with hash and path", () => {
            const text = "nomadnet://1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu";
            const result = LinkUtils.renderReticulumLinks(text);
            expect(result).toContain('class="nomadnet-link');
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
        });

        it("detects nomadnet@ links", () => {
            const text = "nomadnet@1dfeb0d794963579bd21ac8f153c77a4";
            const result = LinkUtils.renderReticulumLinks(text);
            expect(result).toContain('class="nomadnet-link');
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
        });

        it("detects bare hash and path links as nomadnet", () => {
            const text = "1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu";
            const result = LinkUtils.renderReticulumLinks(text);
            expect(result).toContain('class="nomadnet-link');
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
        });

        it("detects bare hash as lxmf", () => {
            const text = "1dfeb0d794963579bd21ac8f153c77a4";
            const result = LinkUtils.renderReticulumLinks(text);
            expect(result).toContain('class="lxmf-link');
            expect(result).toContain('data-lxmf-address="1dfeb0d794963579bd21ac8f153c77a4"');
        });

        it("detects lxmf:// links", () => {
            const text = "lxmf://1dfeb0d794963579bd21ac8f153c77a4";
            const result = LinkUtils.renderReticulumLinks(text);
            expect(result).toContain('class="lxmf-link');
            expect(result).toContain('data-lxmf-address="1dfeb0d794963579bd21ac8f153c77a4"');
        });

        it("detects lxmf@ links", () => {
            const text = "lxmf@1dfeb0d794963579bd21ac8f153c77a4";
            const result = LinkUtils.renderReticulumLinks(text);
            expect(result).toContain('class="lxmf-link');
            expect(result).toContain('data-lxmf-address="1dfeb0d794963579bd21ac8f153c77a4"');
        });
    });

    describe("renderStandardLinks", () => {
        it("detects http links", () => {
            const text = "visit http://example.com";
            const result = LinkUtils.renderStandardLinks(text);
            expect(result).toContain('<a href="http://example.com"');
        });

        it("detects https links", () => {
            const text = "visit https://example.com/path?query=1";
            const result = LinkUtils.renderStandardLinks(text);
            expect(result).toContain('<a href="https://example.com/path?query=1"');
        });

        it("trims trailing punctuation from detected urls", () => {
            const result = LinkUtils.renderStandardLinks("visit https://example.com/path?x=1, now");
            expect(result).toContain('href="https://example.com/path?x=1"');
            expect(result).toContain("</a>, now");
        });

        it("keeps balanced parenthesis in url but trims unmatched trailing one", () => {
            const withBalanced = LinkUtils.renderStandardLinks("see https://example.com/path_(v1)");
            expect(withBalanced).toContain('href="https://example.com/path_(v1)"');

            const withTrailing = LinkUtils.renderStandardLinks("see (https://example.com/path_(v1))");
            expect(withTrailing).toContain('href="https://example.com/path_(v1)"');
            expect(withTrailing).toContain("</a>)");
        });

        it("keeps escaped entity query content in href", () => {
            const text = "visit https://example.com/search?q=a&amp;lang=en";
            const result = LinkUtils.renderStandardLinks(text);
            expect(result).toContain('href="https://example.com/search?q=a&amp;lang=en"');
        });
    });

    describe("renderAllLinks", () => {
        it("detects both types of links", () => {
            const text = "Check https://google.com and nomadnet://1dfeb0d794963579bd21ac8f153c77a4";
            const result = LinkUtils.renderAllLinks(text);
            expect(result).toContain('href="https://google.com"');
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
        });

        it("returns empty string for empty input", () => {
            expect(LinkUtils.renderAllLinks("")).toBe("");
        });

        it("returns string with no links for plain text", () => {
            const result = LinkUtils.renderAllLinks("Just some words.");
            expect(result).toContain("Just some words.");
            expect(result).not.toContain("<a ");
        });

        it("does not double-wrap urls inside existing anchors", () => {
            const original = 'already linked <a href="https://example.com">https://example.com</a>';
            const result = LinkUtils.renderAllLinks(original);
            expect(result).toBe(original);
            expect((result.match(/<a /g) || []).length).toBe(1);
        });

        it("keeps reticulum path underscores", () => {
            const text = "1dfeb0d794963579bd21ac8f153c77a4:/page/meshchatx_on_pi.mu";
            const result = LinkUtils.renderAllLinks(text);
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/meshchatx_on_pi.mu"');
        });
    });

    describe("risky: no script or data URLs in href", () => {
        it("does not produce javascript: href for text containing javascript: URL", () => {
            const text = "see javascript:alert(1) here";
            const result = LinkUtils.renderStandardLinks(text);
            expect(result).not.toMatch(/\bhref\s*=\s*["']?\s*javascript:/i);
        });

        it("does not produce data: href for text containing data: URL", () => {
            const text = "see data:text/html,<script>x</script> here";
            const result = LinkUtils.renderStandardLinks(text);
            expect(result).not.toMatch(/\bhref\s*=\s*["']?\s*data\s*:/i);
        });

        it("does not produce data: href for data image payload text", () => {
            const text = "inline image data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA";
            const result = LinkUtils.renderStandardLinks(text);
            expect(result).not.toMatch(/\bhref\s*=\s*["']?\s*data\s*:/i);
            expect(result).not.toContain("<a ");
        });

        it("stops URL at space so no script in same line", () => {
            const text = "https://example.com javascript:alert(1)";
            const result = LinkUtils.renderStandardLinks(text);
            expect(result).toContain('href="https://example.com"');
            expect(result).not.toMatch(/href="[^"]*javascript:/);
        });

        it("handles null and undefined without throwing", () => {
            expect(LinkUtils.renderReticulumLinks(null)).toBe("");
            expect(LinkUtils.renderReticulumLinks(undefined)).toBe("");
            expect(LinkUtils.renderStandardLinks(null)).toBe("");
        });

        it("handles very long input without hanging", () => {
            const long = "a".repeat(100000);
            const start = Date.now();
            LinkUtils.renderAllLinks(long);
            expect(Date.now() - start).toBeLessThan(200);
        });
    });
});
