// SPDX-License-Identifier: 0BSD

/**
 * Regression tests for bugs found by exploratory probing of hot paths.
 */

import { describe, expect, it } from "vitest";
import MicronParser from "@/js/MicronParser.js";
import { renderNomadHtmlPage, stripOverlayFromCss } from "@/js/NomadPageRenderer.js";
import DownloadUtils from "@/js/DownloadUtils.js";

describe("hot-path bug regressions", () => {
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
});
