// SPDX-License-Identifier: 0BSD

/**
 * Adversarial oracles for XSS and privacy on frontend sanitizers.
 * Expected outcome is computed from the payload (executable URL / dangerous tag)
 * then compared to sanitizer output.
 */

import { describe, expect, it } from "vitest";
import DOMPurify from "dompurify";
import DocsPage from "@/components/docs/DocsPage.vue";
import MarkdownRenderer from "@/js/MarkdownRenderer.js";
import LinkUtils from "@/js/LinkUtils.js";
import { sanitizeNomadHtmlFragment } from "@/js/NomadPageRenderer.js";
import { sanitizeKmlText } from "@/js/mapExchange/kmlSanitize.js";

const EXECUTABLE_HREFS = [
    "javascript:alert(1)",
    "JAVASCRIPT:alert(1)",
    "vbscript:msgbox(1)",
    "data:text/html,<script>alert(1)</script>",
    "data:image/svg+xml,<svg onload=alert(1)>",
];

function assertNoExecutableHtml(html) {
    expect(typeof html).toBe("string");
    const lower = html.toLowerCase();
    expect(lower).not.toMatch(/<script[\s>]/);
    expect(lower).not.toMatch(/<iframe[\s>]/);
    expect(lower).not.toMatch(/\bhref\s*=\s*["']?\s*javascript:/);
    expect(lower).not.toMatch(/\bsrc\s*=\s*["']?\s*javascript:/);
    expect(lower).not.toMatch(/\bhref\s*=\s*["']?\s*vbscript:/);
    expect(lower).not.toMatch(/\bhref\s*=\s*["']?\s*data:text\/html/);
}

describe("adversarial XSS oracles", () => {
    it("chat markdown never emits executable hrefs or script tags", () => {
        for (const href of EXECUTABLE_HREFS) {
            assertNoExecutableHtml(MarkdownRenderer.render(`see ${href} here`));
            assertNoExecutableHtml(MarkdownRenderer.renderBasic(`see ${href} here`));
        }
        assertNoExecutableHtml(MarkdownRenderer.render("<script>alert(1)</script>"));
        assertNoExecutableHtml(MarkdownRenderer.render('<img src=x onerror="alert(1)">'));
        assertNoExecutableHtml(MarkdownRenderer.render("<svg onload=alert(1)>"));
    });

    it("LinkUtils.httpUrlHrefOrNull rejects non-http schemes", () => {
        for (const href of EXECUTABLE_HREFS) {
            expect(LinkUtils.httpUrlHrefOrNull(href)).toBeNull();
        }
        expect(LinkUtils.httpUrlHrefOrNull("https://example.com/a")).toBe("https://example.com/a");
    });

    it("Nomad HTML sanitizer drops script, javascript href, and remote img", () => {
        const html = sanitizeNomadHtmlFragment(
            '<script>alert(1)</script><a href="javascript:alert(1)">x</a>' +
                '<img src="https://evil.example/i.png" onerror="alert(1)">' +
                "<p>ok</p>"
        );
        assertNoExecutableHtml(html);
        expect(html.toLowerCase()).toContain("ok");
        expect(html.toLowerCase()).not.toContain("evil.example");
    });

    it("map draw-feature DOMPurify policy strips script and javascript href", () => {
        const dirty =
            '<script>alert(1)</script><a href="javascript:alert(1)">x</a>' +
            '<img src=x onerror="alert(1)"><p>camp</p>';
        const html = DOMPurify.sanitize(dirty, {
            USE_PROFILES: { html: true },
            FORBID_ATTR: ["style"],
        });
        assertNoExecutableHtml(html);
        expect(html.toLowerCase()).toContain("camp");
    });

    it("Docs search highlight escapes HTML even when the query looks like a tag", () => {
        const highlightMatch = DocsPage.methods.highlightMatch;
        const html = highlightMatch.call({ searchQuery: "<script>" }, '<img onerror="alert(1)"> hello <script>');
        assertNoExecutableHtml(html);
        expect(html).toContain("&lt;");
        expect(html).not.toContain("<img");
        expect(html).not.toContain("<script>");
    });

    it("KML sanitizer strips xlink href, vbscript, and nested description HTML", () => {
        const kml = `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:xlink="http://www.w3.org/1999/xlink"><Document>
<Placemark><name>P</name>
<description><a href="javascript:alert(1)">x</a></description>
<Style><IconStyle><Icon xlink:href="https://evil.example/i.png"></Icon></IconStyle></Style>
<Style><IconStyle><Icon><href>vbscript:msgbox(1)</href></Icon></IconStyle></Style>
<Point><coordinates>1,2,0</coordinates></Point>
</Placemark></Document></kml>`;
        const out = sanitizeKmlText(kml);
        const lower = out.text.toLowerCase();
        expect(lower).not.toContain("https://evil.example");
        expect(lower).not.toContain("javascript:");
        expect(lower).not.toContain("vbscript:");
        expect(lower).not.toContain("<a ");
        expect(lower).toContain("placemark");
        expect(out.stripped.length).toBeGreaterThan(0);
    });
});
