// SPDX-License-Identifier: 0BSD

/**
 * Shared XSS corpus against every HTML sanitizer the UI ships.
 * Formatted markup may remain. Scriptable nodes and executable URLs must not.
 */

import { describe, expect, it } from "vitest";
import MarkdownRenderer from "@/js/MarkdownRenderer.js";
import MicronParser from "@/js/MicronParser.js";
import {
    renderNomadHtmlPage,
    renderNomadMarkdown,
    sanitizeNomadHtmlDocument,
    sanitizeNomadHtmlFragment,
} from "@/js/NomadPageRenderer.js";
import { sanitizeKmlText } from "@/js/mapExchange/kmlSanitize.js";

export const XSS_PAYLOADS = [
    { name: "javascript href", input: '<a href="javascript:alert(1)">x</a>' },
    { name: "javascript uppercase", input: '<a href="JAVASCRIPT:alert(1)">x</a>' },
    { name: "data html href", input: '<a href="data:text/html,<script>alert(1)</script>">x</a>' },
    { name: "base tag", input: '<base href="https://evil.example/"><p>ok</p>' },
    { name: "svg script", input: "<svg><script>alert(1)</script></svg><p>ok</p>" },
    { name: "svg onload", input: '<svg onload="alert(1)"></svg><p>ok</p>' },
    { name: "img onerror", input: '<img src=x onerror="alert(1)"><p>ok</p>' },
    {
        name: "css url javascript",
        input: '<style>body{background:url("javascript:alert(1)")}</style><p>ok</p>',
    },
    {
        name: "css url https",
        input: '<style>p{background:url("https://evil.example/x.png")}</style><p>ok</p>',
    },
    { name: "nested markdown js", input: "[x](javascript:alert(1))" },
    { name: "nested markdown image", input: "![x](javascript:alert(1))" },
    { name: "script tag", input: "<script>alert(1)</script><p>ok</p>" },
    { name: "iframe", input: '<iframe src="javascript:alert(1)"></iframe><p>ok</p>' },
    { name: "micron js link", input: "`[click`javascript:alert(1)]`" },
    { name: "entity javascript href", input: '<a href="&#106;avascript:alert(1)">x</a>' },
];

export function assertNoScriptableHtml(html, payloadName) {
    expect(typeof html, payloadName).toBe("string");
    const doc = new DOMParser().parseFromString(`<div id="xss-root">${html}</div>`, "text/html");
    const root = doc.getElementById("xss-root") || doc.body;
    expect(root.querySelector("script, iframe, object, embed, base"), payloadName).toBeNull();
    for (const el of root.querySelectorAll("[href], [src]")) {
        for (const attr of ["href", "src"]) {
            const v = el.getAttribute(attr);
            if (!v) {
                continue;
            }
            const lower = v.trim().toLowerCase();
            expect(lower.startsWith("javascript:"), `${payloadName} ${attr}`).toBe(false);
            expect(lower.startsWith("vbscript:"), `${payloadName} ${attr}`).toBe(false);
            expect(lower.startsWith("data:text/html"), `${payloadName} ${attr}`).toBe(false);
        }
    }
    for (const el of root.querySelectorAll("*")) {
        for (const attr of [...el.attributes]) {
            expect(attr.name.toLowerCase().startsWith("on"), `${payloadName} ${attr.name}`).toBe(false);
        }
    }
    for (const styleEl of root.querySelectorAll("style")) {
        const css = (styleEl.textContent || "").toLowerCase();
        expect(css, payloadName).not.toMatch(/url\s*\(\s*["']?\s*javascript:/);
        expect(css, payloadName).not.toMatch(/expression\s*\(/);
    }
    for (const el of root.querySelectorAll("[style]")) {
        const css = (el.getAttribute("style") || "").toLowerCase();
        expect(css, payloadName).not.toMatch(/url\s*\(\s*["']?\s*javascript:/);
    }
}

function wrapKml(inner) {
    return `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>P</name>
<description><![CDATA[${inner}]]></description>
<Point><coordinates>1,2,0</coordinates></Point>
</Placemark></Document></kml>`;
}

describe("shared XSS sanitizer oracles", () => {
    it("MarkdownRenderer never emits a scriptable node", () => {
        for (const { name, input } of XSS_PAYLOADS) {
            assertNoScriptableHtml(MarkdownRenderer.render(input), `render ${name}`);
            assertNoScriptableHtml(MarkdownRenderer.renderBasic(input), `renderBasic ${name}`);
        }
    });

    it("Nomad HTML and markdown sanitizers never emit a scriptable node", () => {
        for (const { name, input } of XSS_PAYLOADS) {
            assertNoScriptableHtml(sanitizeNomadHtmlFragment(input), `fragment ${name}`);
            assertNoScriptableHtml(sanitizeNomadHtmlDocument(input), `document ${name}`);
            assertNoScriptableHtml(renderNomadHtmlPage(input), `html page ${name}`);
            assertNoScriptableHtml(renderNomadMarkdown(input), `markdown ${name}`);
        }
    });

    it("MicronParser never emits a scriptable node", () => {
        const parser = new MicronParser(true, false);
        for (const { name, input } of XSS_PAYLOADS) {
            assertNoScriptableHtml(MicronParser.sanitizeRenderedMicronHtml(input), `sanitize ${name}`);
            assertNoScriptableHtml(parser.convertMicronToHtml(input), `convert ${name}`);
        }
    });

    it("Micron overlay scrub strips unquoted position:fixed", () => {
        const html = MicronParser.sanitizeRenderedMicronHtml("<div style=position:fixed;top:0;width:100%>tap</div>");
        const lower = html.toLowerCase();
        expect(lower).not.toMatch(/position\s*:\s*fixed/);
    });

    it("KML sanitizer never emits a scriptable node", () => {
        for (const { name, input } of XSS_PAYLOADS) {
            const out = sanitizeKmlText(wrapKml(input));
            assertNoScriptableHtml(out.text, `kml ${name}`);
            const lower = out.text.toLowerCase();
            expect(lower, `kml href ${name}`).not.toMatch(/<href>\s*(javascript:|vbscript:|data:text\/html)/);
            expect(lower, `kml xlink ${name}`).not.toMatch(/xlink:href\s*=\s*["']?\s*javascript:/);
        }
    });
});
