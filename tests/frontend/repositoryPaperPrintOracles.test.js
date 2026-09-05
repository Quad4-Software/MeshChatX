// SPDX-License-Identifier: 0BSD

/**
 * Oracles for repository URL href guards and paper print HTML escaping.
 */

import { describe, expect, it, vi } from "vitest";
import LinkUtils from "@/js/LinkUtils.js";
import Utils from "@/js/Utils.js";
import { computeBrowserRepoUrl } from "@/features/repository-server/lib/repositoryServer.ts";
import { printPaperQr } from "@/features/paper-message/lib/paperPrint.ts";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("repository URL and print XSS oracles", () => {
    it("browserRepoUrl only returns http(s) without credentials", () => {
        const cases = [
            ["javascript:alert(1)", null],
            ["data:text/html,x", null],
            ["file:///tmp/x", null],
            ["not a url", null],
            ["http://user:pass@evil.example/", null],
            ["http://127.0.0.1:8787/", "http://127.0.0.1:8787/"],
            ["https://example.com/repo", "https://example.com/repo"],
        ];
        for (const [raw, expected] of cases) {
            const href = computeBrowserRepoUrl(raw);
            expect(href).toBe(expected);
            if (expected) {
                expect(LinkUtils.httpUrlHrefOrNull(href)).toBe(href);
            }
        }
    });

    it("browserRepoUrl rewrites 0.0.0.0 then still requires http(s)", () => {
        const href = computeBrowserRepoUrl("http://0.0.0.0:9999/x");
        expect(href).toMatch(/^http:\/\/[^/]+:9999\/x$/);
        expect(href).not.toContain("0.0.0.0");
        expect(LinkUtils.httpUrlHrefOrNull(href)).toBe(href);
    });

    it("printPaperQr escapes destinationHash in document.write", () => {
        const writes = [];
        const printWindow = {
            document: {
                write: (html) => writes.push(html),
                close: vi.fn(),
            },
        };
        const openSpy = vi.spyOn(window, "open").mockReturnValue(printWindow);
        const canvas = {
            toDataURL: () => "data:image/png;base64,abc",
        };
        const destinationHash = '</div><script>alert(1)</script><div class="x">';
        const ok = printPaperQr({
            canvas,
            destinationHash,
        });
        expect(ok).toBe(true);
        expect(writes.length).toBe(1);
        const html = writes[0];
        const recipient = html.match(/Recipient:\s*([^<]*)/);
        expect(recipient?.[1]).toBe(Utils.escapeHtml(destinationHash));
        expect(html).toContain("&lt;script&gt;");
        expect(html).not.toMatch(/Recipient:\s*<\/div><script/i);
        openSpy.mockRestore();
    });

    it("PaperMessageModal escapes dynamic print HTML fields", () => {
        const source = readFileSync(
            resolve(
                process.cwd(),
                "meshchatx/src/frontend/features/messages/components/modals/PaperMessageModal.svelte"
            ),
            "utf8"
        );
        expect(source).toContain("Utils.escapeHtml(dataUrl)");
        expect(source).toContain('Utils.escapeHtml(messageHash || "")');
    });
});
