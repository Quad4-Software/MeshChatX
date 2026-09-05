// SPDX-License-Identifier: 0BSD

/**
 * Oracles for repository URL href guards and paper print HTML escaping.
 */

import { describe, expect, it, vi } from "vitest";
import LinkUtils from "@/js/LinkUtils.js";
import Utils from "@/js/Utils.js";
import RepositoryServerPage from "@/components/tools/RepositoryServerPage.vue";
import PaperMessagePage from "@/components/tools/PaperMessagePage.vue";
import PaperMessageModal from "@/components/messages/modals/PaperMessageModal.vue";

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
            const href = RepositoryServerPage.computed.browserRepoUrl.call({
                status: { http: { url: raw } },
            });
            expect(href).toBe(expected);
            if (expected) {
                expect(LinkUtils.httpUrlHrefOrNull(href)).toBe(href);
            }
        }
    });

    it("browserRepoUrl rewrites 0.0.0.0 then still requires http(s)", () => {
        const href = RepositoryServerPage.computed.browserRepoUrl.call({
            status: { http: { url: "http://0.0.0.0:9999/x" } },
        });
        expect(href).toMatch(/^http:\/\/[^/]+:9999\/x$/);
        expect(href).not.toContain("0.0.0.0");
        expect(LinkUtils.httpUrlHrefOrNull(href)).toBe(href);
    });

    it("PaperMessagePage printQRCode escapes destinationHash in document.write", () => {
        const writes = [];
        const printWindow = {
            document: {
                write: (html) => writes.push(html),
                close: vi.fn(),
            },
        };
        const openSpy = vi.spyOn(window, "open").mockReturnValue(printWindow);
        const ctx = {
            $refs: {
                qrcode: {
                    toDataURL: () => "data:image/png;base64,abc",
                },
            },
            destinationHash: '</div><script>alert(1)</script><div class="x">',
            $t: (k) => k,
        };
        PaperMessagePage.methods.printQRCode.call(ctx);
        expect(writes.length).toBe(1);
        const html = writes[0];
        const recipient = html.match(/Recipient:\s*([^<]*)/);
        expect(recipient?.[1]).toBe(Utils.escapeHtml(ctx.destinationHash));
        expect(html).toContain("&lt;script&gt;");
        expect(html).not.toMatch(/Recipient:\s*<\/div><script/i);
        openSpy.mockRestore();
    });

    it("PaperMessageModal printQRCode escapes messageHash in document.write", () => {
        const writes = [];
        const printWindow = {
            document: {
                write: (html) => writes.push(html),
                close: vi.fn(),
            },
        };
        const openSpy = vi.spyOn(window, "open").mockReturnValue(printWindow);
        const ctx = {
            $refs: {
                qrcode: {
                    toDataURL: () => "data:image/png;base64,abc",
                },
            },
            messageHash: "</div><img src=x onerror=alert(1)>",
            $t: (k) => k,
        };
        PaperMessageModal.methods.printQRCode.call(ctx);
        expect(writes.length).toBe(1);
        const html = writes[0];
        const hashLine = html.match(/Message Hash:\s*([^<]*)/);
        expect(hashLine?.[1]).toBe(Utils.escapeHtml(ctx.messageHash));
        expect(html).toContain("&lt;img");
        expect(html).not.toMatch(/Message Hash:\s*<\/div><img/i);
        openSpy.mockRestore();
    });
});
