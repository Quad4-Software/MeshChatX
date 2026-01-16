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
    });

    describe("renderAllLinks", () => {
        it("detects both types of links", () => {
            const text = "Check https://google.com and nomadnet://1dfeb0d794963579bd21ac8f153c77a4";
            const result = LinkUtils.renderAllLinks(text);
            expect(result).toContain('href="https://google.com"');
            expect(result).toContain('data-nomadnet-url="1dfeb0d794963579bd21ac8f153c77a4:/page/index.mu"');
        });
    });
});
