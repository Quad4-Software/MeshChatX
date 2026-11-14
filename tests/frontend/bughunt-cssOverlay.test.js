// SPDX-License-Identifier: 0BSD
// Bug-hunt: NomadPageRenderer / nomadCssSecurity overlay-CSS bypasses.
import { describe, expect, it } from "vitest";
import {
    sanitizeNomadHtmlDocument,
    sanitizeNomadHtmlFragment,
    renderNomadHtmlPage,
    renderNomadMarkdown,
} from "../../meshchatx/src/frontend/js/NomadPageRenderer.js";
import MicronParser from "../../meshchatx/src/frontend/js/MicronParser.js";
import { stripOverlayFromCss, stripExternalFromCss } from "../../meshchatx/src/frontend/js/NomadPageRenderer.js";

// Extract every <style> block body from sanitized output.
function styleBlocks(html) {
    const out = [];
    const re = /<style[^>]*>([\s\S]*?)<\/style>/gi;
    let m;
    while ((m = re.exec(html))) {
        out.push(m[1]);
    }
    return out;
}

describe("bughunt: nomad CSS overlay bypass", () => {
    it("in-body <style> keeps unscoped body{} selectors (selector rewrite skipped)", () => {
        // bodyMarkup = rewritten-collected-styles + body.innerHTML. The
        // in-body <style> is collected for rewriting AND left verbatim in
        // body.innerHTML, so the verbatim copy keeps `body`/`html` selectors.
        const out = sanitizeNomadHtmlDocument('<p>hi</p><style>body{display:none}</style>');
        const blocks = styleBlocks(out);
        // The rewritten copy should target .nomad-html-root only.
        const dangerous = blocks.filter((b) => /(^|[}\s,])(?:body|html)\s*[,{]/.test(b) || /\bbody\s*\{/.test(b));
        // BUG: a verbatim `body{display:none}` survives -> hides the whole app.
        expect(dangerous, `unscoped body/html selector survived: ${JSON.stringify(blocks)}`).toEqual([]);
    });

    it("in-body <style> html{} selector survives verbatim", () => {
        const out = sanitizeNomadHtmlDocument('<style>html{background:red}</style><p>x</p>');
        const blocks = styleBlocks(out);
        const dangerous = blocks.filter((b) => /\bhtml\s*\{/.test(b));
        expect(dangerous, `unscoped html selector survived: ${JSON.stringify(blocks)}`).toEqual([]);
    });

    it("position:fixed via CSS custom property survives stripOverlayFromCss", () => {
        const css = ".x{--p:fixed;position:var(--p)}";
        const out = stripOverlayFromCss(css);
        // The scrubber must neutralize computed position:fixed. var() is a
        // computed-value indirection it does not resolve.
        expect(out, `var()-indirected position survived: ${out}`).not.toMatch(/position\s*:\s*var\(/i);
    });

    it("position:fixed via var() survives inline style scrubbing", () => {
        const html = '<div style="--p:fixed;position:var(--p);width:100dvw;height:100dvh">x</div>';
        const out = MicronParser.stripOverlayStyles(html);
        expect(out, `style attr bypass survived: ${out}`).not.toMatch(/position\s*:\s*var\(/i);
        expect(out, `100dvw survived: ${out}`).not.toMatch(/100dvw/i);
    });

    it("100dvw/100svw viewport units bypass the 100v[wh] guard", () => {
        const css = ".x{width:100dvw;height:100lvh}";
        const out = stripOverlayFromCss(css);
        expect(out, `dynamic viewport units survived: ${out}`).not.toMatch(/100[dsl][vwh]/i);
    });

    it("full overlay chain via var()+dvw in a <style> block", () => {
        const css = ".x{--p:fixed;position:var(--p);width:100dvw;height:100dvh;background:#fff}";
        const out = stripExternalFromCss(css);
        // Every ingredient of a viewport-covering overlay must be neutralized.
        expect(out).not.toMatch(/position\s*:\s*var\(/i);
        expect(out).not.toMatch(/100dvw/i);
        expect(out).not.toMatch(/100dvh/i);
    });

    it("margin/translate survive and can re-position a fixed element", () => {
        const css = ".x{position:var(--p);margin-top:-100vh;translate:0 -50%}";
        const out = stripOverlayFromCss(css);
        // margin-top and the individual `translate` property are not stripped,
        // so even with top/left removed an overlay can be dragged over the UI.
        expect(out).not.toMatch(/margin-top/i);
        expect(out).not.toMatch(/\btranslate\s*:/i);
    });

    it("renderNomadHtmlPage emits unscoped body selector from in-body style", () => {
        const out = renderNomadHtmlPage('<div>ok</div><style>body *{visibility:hidden}</style>');
        expect(out).not.toMatch(/body\s*\*\s*\{/);
    });

    it("markdown inline HTML style attribute keeps var() position", () => {
        const out = renderNomadMarkdown('<div style="--p:fixed;position:var(--p);width:100dvw;height:100dvh">x</div>');
        expect(out).not.toMatch(/position\s*:\s*var\(/i);
    });
});
