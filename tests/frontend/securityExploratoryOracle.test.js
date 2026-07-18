// SPDX-License-Identifier: 0BSD

/**
 * Exploratory fuzzing and light oracles for Micron/Nomad/codec2/memory hardening.
 *
 * Light oracles = invariant checks on every output (no full differential engine):
 *  - no script / javascript / iframe / fixed overlays after sanitize
 *  - codec2 size gate rejects oversize and accepts undersize
 *  - memory warning classifier ignores non-memory kinds
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import MicronParser from "@/js/MicronParser.js";
import {
    renderNomadHtmlPage,
    renderNomadMarkdown,
    sanitizeNomadHtmlFragment,
    stripExternalFromCss,
    stripOverlayFromCss,
} from "@/js/NomadPageRenderer.js";
import {
    MAX_CODEC2_DECODED_RAW_BYTES,
    MAX_CODEC2_ENCODED_BYTES,
    assertByteLengthAtMost,
} from "@/js/codec2DecodeLimits.js";
import {
    evaluateClientHeapSample,
    handleHealthWarningPayload,
    isMemoryHealthWarningPayload,
    resetMemoryWarningStateForTests,
} from "@/js/healthMemoryWarning.js";

const DANGEROUS_TAGS = [/<script[\s>]/i, /<iframe[\s>]/i, /<object[\s>]/i, /<embed[\s>]/i];

const OVERLAY_STYLE_ATTACKS = [
    'style="position:fixed !important; inset:0; z-index:99999"',
    'style="position/**/:fixed; top:0; left:0"',
    'style="position: sticky !important; transform: translateY(0)"',
    'style="POSITION:FiXeD; width:100vw; height:100vh"',
    `style="position:fi${String.fromCharCode(0x200b)}xed; inset:0"`,
    `style="position:fi${String.fromCharCode(0x00ad)}xed"`,
];

function assertSafeHtmlOracle(html) {
    expect(typeof html).toBe("string");
    const lower = html.toLowerCase();
    for (const re of DANGEROUS_TAGS) {
        expect(html).not.toMatch(re);
    }
    // Executable URL contexts only (plain text mentioning javascript: is fine).
    expect(lower).not.toMatch(/\bhref\s*=\s*["']?\s*javascript\s*:/);
    expect(lower).not.toMatch(/\bsrc\s*=\s*["']?\s*javascript\s*:/);
    expect(lower).not.toMatch(/\bhref\s*=\s*["']?\s*vbscript\s*:/);
    expect(lower).not.toMatch(/position\s*:\s*fixed/);
    expect(lower).not.toMatch(/position\s*:\s*sticky/);
}

function randomStyleValue(len) {
    const tokens = [
        "position:fixed",
        "position:fixed !important",
        "position/**/:fixed",
        "position:sticky",
        "inset:0",
        "z-index:99999",
        "top:0",
        "left:0",
        "transform:scale(1)",
        "width:100vw",
        "height:100vh",
        "color:red",
        "font-size:12px",
        "background:#fff",
        "/*comment*/",
        "",
    ];
    const parts = [];
    for (let i = 0; i < len; i++) {
        parts.push(tokens[Math.floor(Math.random() * tokens.length)]);
    }
    return parts.join("; ");
}

function randomHtmlSnippet() {
    const snippets = [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<a href=javascript:alert(1)>x</a>",
        "<svg onload=alert(1)>",
        "<iframe src=https://evil></iframe>",
        "<style>@import url(http://x); body{position:fixed}</style>",
        '<div style="position:fixed !important">phish</div>',
        "<p onclick=alert(1)>x</p>",
        "normal text " + String.fromCharCode(0x1f4a3),
        "<a href='vbscript:msgbox(1)'>x</a>",
    ];
    return snippets[Math.floor(Math.random() * snippets.length)];
}

describe("exploratory + oracle-light: Micron overlay strip", () => {
    it("oracle: known overlay attacks lose fixed/sticky", () => {
        for (const attack of OVERLAY_STYLE_ATTACKS) {
            const html = MicronParser.stripOverlayStyles(`<div ${attack}>x</div>`);
            assertSafeHtmlOracle(html);
            expect(html).toContain("x");
        }
    });

    it("exploratory: random style attributes never throw and never keep fixed/sticky", () => {
        for (let i = 0; i < 300; i++) {
            const style = randomStyleValue(1 + (i % 8));
            let out;
            expect(() => {
                out = MicronParser.stripOverlayStyles(`<span style="${style}">n</span>`);
            }).not.toThrow();
            assertSafeHtmlOracle(out);
        }
    });

    it("exploratory: sanitizeRenderedMicronHtml on mixed XSS payloads", () => {
        for (let i = 0; i < 200; i++) {
            const payload =
                randomHtmlSnippet() +
                (i % 3 === 0 ? `<div ${OVERLAY_STYLE_ATTACKS[i % OVERLAY_STYLE_ATTACKS.length]}>z</div>` : "");
            let out;
            expect(() => {
                out = MicronParser.sanitizeRenderedMicronHtml(payload);
            }).not.toThrow();
            assertSafeHtmlOracle(out);
        }
    });
});

describe("exploratory + oracle-light: Nomad HTML/MD/CSS", () => {
    it("oracle: style-block overlays are neutralized", () => {
        const css = stripOverlayFromCss(".x{position:fixed !important;inset:0;z-index:9}");
        expect(css.toLowerCase()).not.toMatch(/position\s*:\s*fixed/);
        expect(stripExternalFromCss("@import url(http://x); .a{position:sticky}")).not.toMatch(/@import/i);
    });

    it("exploratory: renderNomadHtmlPage random payloads stay within oracle", () => {
        for (let i = 0; i < 250; i++) {
            let s = randomHtmlSnippet();
            const extra = Math.floor(Math.random() * 400);
            for (let j = 0; j < extra; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 128));
            }
            let out;
            expect(() => {
                out = renderNomadHtmlPage(`<body>${s}</body>`);
            }).not.toThrow();
            assertSafeHtmlOracle(out);
        }
    });

    it("exploratory: markdown + fragment path respect oracle", () => {
        for (let i = 0; i < 120; i++) {
            const md = `${"#".repeat(1 + (i % 3))} title ${i}\n\n[x](javascript:alert(1))\n\n<div style="position:fixed">y</div>`;
            let html;
            let frag;
            expect(() => {
                html = renderNomadMarkdown(md);
                frag = sanitizeNomadHtmlFragment(`<div>${randomHtmlSnippet()}</div>`);
            }).not.toThrow();
            assertSafeHtmlOracle(html);
            assertSafeHtmlOracle(frag);
        }
    });
});

describe("exploratory + oracle-light: codec2 size gate", () => {
    it("oracle: under-cap buffers pass, over-cap buffers throw", () => {
        expect(assertByteLengthAtMost(new Uint8Array(0), MAX_CODEC2_ENCODED_BYTES).byteLength).toBe(0);
        expect(assertByteLengthAtMost(new Uint8Array(16), MAX_CODEC2_ENCODED_BYTES).byteLength).toBe(16);
        expect(() =>
            assertByteLengthAtMost(new Uint8Array(MAX_CODEC2_ENCODED_BYTES + 1), MAX_CODEC2_ENCODED_BYTES)
        ).toThrow(/exceeds size limit/);
        expect(() =>
            assertByteLengthAtMost(new Uint8Array(MAX_CODEC2_DECODED_RAW_BYTES + 1), MAX_CODEC2_DECODED_RAW_BYTES)
        ).toThrow(/exceeds size limit/);
    });

    it("exploratory: random sizes near boundaries behave as oracle predicts", () => {
        const cases = [
            0,
            1,
            MAX_CODEC2_ENCODED_BYTES - 1,
            MAX_CODEC2_ENCODED_BYTES,
            MAX_CODEC2_ENCODED_BYTES + 1,
            Math.floor(Math.random() * MAX_CODEC2_ENCODED_BYTES),
        ];
        for (const n of cases) {
            const buf = new Uint8Array(Math.max(0, n));
            if (n <= MAX_CODEC2_ENCODED_BYTES) {
                expect(assertByteLengthAtMost(buf, MAX_CODEC2_ENCODED_BYTES).byteLength).toBe(n);
            } else {
                expect(() => assertByteLengthAtMost(buf, MAX_CODEC2_ENCODED_BYTES)).toThrow(/exceeds size limit/);
            }
        }
    });
});

describe("exploratory + oracle-light: memory warning classifier", () => {
    beforeEach(() => {
        resetMemoryWarningStateForTests();
    });

    it("oracle: only memory_low shows toast; other kinds ignored", () => {
        const toast = { warning: vi.fn() };
        const ignored = [
            null,
            undefined,
            "memory_low",
            { kind: "entropy_climbing" },
            { kind: "error_rate_high" },
            { type: "health_warning", data: { kind: "entropy_climbing" } },
            { data: { kind: "something_else" } },
        ];
        for (const payload of ignored) {
            expect(isMemoryHealthWarningPayload(payload)).toBe(false);
            expect(handleHealthWarningPayload(payload, toast)).toBe("ignored");
        }
        expect(toast.warning).not.toHaveBeenCalled();
        expect(handleHealthWarningPayload({ data: { kind: "memory_low" } }, toast)).toBe("shown");
        expect(toast.warning).toHaveBeenCalledTimes(1);
    });

    it("exploratory: random heap samples never throw; single spike is not a warn", () => {
        for (let i = 0; i < 200; i++) {
            const limit = 1000 + Math.floor(Math.random() * 9000);
            const used = Math.floor(Math.random() * limit * 1.2);
            let result;
            expect(() => {
                result = evaluateClientHeapSample({
                    jsHeapSizeLimit: limit,
                    usedJSHeapSize: used,
                });
            }).not.toThrow();
            expect(typeof result.shouldWarn).toBe("boolean");
            expect(typeof result.reason).toBe("string");
        }
        resetMemoryWarningStateForTests();
        const oneSpike = evaluateClientHeapSample({
            jsHeapSizeLimit: 1000,
            usedJSHeapSize: 900,
        });
        expect(oneSpike.shouldWarn).toBe(false);
        expect(oneSpike.reason).toBe("need_consecutive");
    });
});
