// SPDX-License-Identifier: 0BSD

/**
 * Regression tests for bugs found by exploratory probing of hot paths.
 */

import { describe, expect, it } from "vitest";
import MicronParser from "@/js/MicronParser.js";
import { renderNomadHtmlPage, stripOverlayFromCss } from "@/js/NomadPageRenderer.js";
import DownloadUtils from "@/js/DownloadUtils.js";

describe("hot-path bug regressions", () => {
    it("strips absolute full-bleed overlays and rejects svg data images", () => {
        const css = stripOverlayFromCss(".x{position:absolute;top:0;left:0;width:100%;height:100%;z-index:9}");
        expect(css.toLowerCase()).not.toMatch(/position\s*:\s*absolute/);
        expect(css.toLowerCase()).toMatch(/position:static/);
        const svg =
            "data:image/svg+xml," +
            encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>');
        const html = renderNomadHtmlPage(`<img src="${svg}"><img src="data:image/png;base64,aaa">`);
        expect(html.toLowerCase()).not.toContain("svg+xml");
        expect(html).toContain("data:image/png");
    });

    it("strips single-quoted position:fixed overlays", () => {
        const out = MicronParser.stripOverlayStyles(`<div style='position:fixed; color:red'>x</div>`);
        expect(out.toLowerCase()).not.toMatch(/position\s*:\s*fixed/);
        expect(out).toContain("color:red");
    });

    it("strips CSS hex-escaped fixed (fixe\\64) in style blocks", () => {
        const out = stripOverlayFromCss("x{position:fixe\\64;inset:0}");
        expect(out.toLowerCase()).not.toMatch(/fixe\\64/);
        expect(out.toLowerCase()).not.toMatch(/position\s*:\s*fixed/);
        expect(out.toLowerCase()).toContain("position:static");
    });

    it("Nomad HTML render neutralises CSS-escaped fixed overlays", () => {
        const html = renderNomadHtmlPage(
            "<body><style>.x{position:fixe\\64;inset:0;z-index:9}</style><div class=x>y</div></body>"
        );
        expect(html.toLowerCase()).not.toMatch(/fixe\\64/);
        expect(html.toLowerCase()).not.toMatch(/position\s*:\s*fixed/);
    });

    it("download filenames drop path traversal segments", () => {
        expect(
            DownloadUtils.parseFilenameFromContentDisposition('attachment; filename="../../evil.html"', "safe.bin")
        ).toBe("evil.html");
        expect(DownloadUtils.sanitizeDownloadFilename("../a/b\\c.txt", "x.bin")).toBe("c.txt");
        expect(DownloadUtils.sanitizeDownloadFilename("..", "x.bin")).toBe("x.bin");
    });

    it("download filenames strip CR/LF/NUL", () => {
        expect(DownloadUtils.sanitizeDownloadFilename("a\r\nb.html", "x.bin")).toBe("ab.html");
        expect(DownloadUtils.sanitizeDownloadFilename("a\x00b.bin", "x.bin")).toBe("ab.bin");
    });

    it("strips zero-width and soft-hyphen hidden fixed overlays", () => {
        const zwsp = String.fromCharCode(0x200b);
        const shyChar = String.fromCharCode(0x00ad);
        const zw = MicronParser.stripOverlayStyles(`<div style="position:fi${zwsp}xed; color:red">x</div>`);
        expect(zw.toLowerCase()).not.toMatch(/position\s*:\s*fi/);
        expect(zw).toContain("color:red");
        const shy = MicronParser.stripOverlayStyles(`<div style="position:fi${shyChar}xed">x</div>`);
        expect(shy.toLowerCase()).not.toMatch(/position\s*:/);
        const cssZw = stripOverlayFromCss(`.x{position:fi${zwsp}xed;inset:0}`);
        expect(cssZw.toLowerCase()).not.toMatch(/position\s*:\s*fi/);
        expect(cssZw.toLowerCase()).toMatch(/position:static/);
    });

    it("download filenames strip bidi overrides and Windows reserved names", () => {
        const rtl = String.fromCharCode(0x202e);
        expect(DownloadUtils.sanitizeDownloadFilename(`${rtl}exe.txt`, "x.bin")).toBe("exe.txt");
        expect(DownloadUtils.sanitizeDownloadFilename("CON.txt", "x.bin")).toBe("x.bin");
        expect(DownloadUtils.sanitizeDownloadFilename("evil.txt...", "x.bin")).toBe("evil.txt");
    });
});
