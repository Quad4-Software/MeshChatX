// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import ArchivesPage from "@/components/archives/ArchivesPage.vue";

function mountArchives() {
    const routerPush = vi.fn();
    return {
        wrapper: mount(ArchivesPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: { push: routerPush },
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        }),
        routerPush,
    };
}

function randText(len) {
    const alphabet = "abc<>\"'`\\/\u0000\n\r`topic_id=";
    let s = "";
    for (let i = 0; i < len; i++) {
        s += alphabet[(Math.random() * alphabet.length) | 0];
    }
    return s;
}

function assertNoDangerousHtmlPatterns(html) {
    const lower = html.toLowerCase();
    expect(lower).not.toContain("<script");
    expect(lower).not.toContain("<iframe");
    expect(lower).not.toContain("javascript:");
    expect(lower).not.toMatch(/<[^>]*\bonerror\s*=/);
    expect(lower).not.toMatch(/<[^>]*\bonload\s*=/);
}

describe("Archives page viewing-archive surface (security / fuzz)", () => {
    const nastyPaths = [
        "/page/article.mu`topic_id=40",
        "/page/article.mu`topic_id=40`extra",
        "/forum/thread.mu`sort=hot",
        "/../../../etc/passwd",
        "javascript:alert(1)",
        "<script>alert(1)</script>",
        "a".repeat(6000),
    ];

    const nastyContents = [
        "<img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>",
        "`>>{{constructor.constructor('return this')()}}",
        "# Title\n[link](javascript:alert(1))",
        "\x00".repeat(20),
    ];

    it("renderFullContent sanitizes .html archives", () => {
        const { wrapper } = mountArchives();
        const out = wrapper.vm.renderFullContent({
            page_path: "/page/evil.html",
            content: '<body><img src=x onerror=alert(1)><a href="javascript:alert(1)">x</a></body>',
            destination_hash: "a".repeat(32),
            hash: "b".repeat(32),
            id: 1,
        });
        assertNoDangerousHtmlPatterns(out);
    });

    it("heuristic micron archives isolate http and mesh links", () => {
        const { wrapper } = mountArchives();
        const hash = "aa".repeat(16);
        const out = wrapper.vm.renderFullContent({
            page_path: "/forum/thread",
            content:
                "`Hi`\n`[Phish`http://evil.example/login]`\n`[Node`bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb:/page/index.mu]`",
            destination_hash: hash,
            id: 2,
        });
        expect(out.toLowerCase()).not.toMatch(/href\s*=\s*["']?\s*https?:/i);
        expect(out).toMatch(/data-action\s*=\s*["']openNode["']/i);
    });

    it("renderFullContent never throws; returns a string for fuzzed paths and bodies", () => {
        const { wrapper } = mountArchives();
        for (let i = 0; i < 90; i++) {
            const page_path = nastyPaths[i % nastyPaths.length] + randText(i % 7);
            const content = nastyContents[i % nastyContents.length] + randText(40);
            const archive = {
                page_path,
                content,
                destination_hash: "a".repeat(64),
                hash: "b".repeat(64),
                id: i + 1,
            };
            expect(() => wrapper.vm.renderFullContent(archive)).not.toThrow();
            const out = wrapper.vm.renderFullContent(archive);
            expect(typeof out).toBe("string");
            if ((archive.page_path || "").split("`")[0].toLowerCase().endsWith(".html")) {
                assertNoDangerousHtmlPatterns(out);
            }
        }
    });

    it("archiveViewerClasses picks safe viewer classes for adversarial page_path values", () => {
        const { wrapper } = mountArchives();
        const cases = [
            { page_path: "/page/article.mu`topic_id=40", expectRich: true },
            { page_path: "/page/readme.html", expectRich: true, expectHtml: true },
            { page_path: "javascript:alert(1)", expectRich: false },
            { page_path: "../../../etc/passwd", expectRich: false },
        ];
        for (const { page_path, expectRich, expectHtml } of cases) {
            wrapper.vm.viewingArchive = { page_path };
            const classes = wrapper.vm.archiveViewerClasses;
            expect(Array.isArray(classes)).toBe(true);
            expect(classes).toContain("wrap-break-word");
            expect(classes.includes("nomad-page-rich")).toBe(expectRich);
            if (expectHtml) {
                expect(classes).toContain("nomad-page-html-host");
            }
        }
        wrapper.vm.viewingArchive = null;
    });

    it("openInNomadnet uses router.push with nomadnetwork route and query only", () => {
        const { wrapper, routerPush } = mountArchives();
        wrapper.vm.openInNomadnet({
            id: 40,
            destination_hash: "deadbeef",
            page_path: "/page/article.mu`topic_id=40",
        });
        expect(routerPush).toHaveBeenCalledWith({
            name: "nomadnetwork",
            params: { destinationHash: "deadbeef" },
            query: {
                path: "/page/article.mu`topic_id=40",
                archive_id: 40,
            },
        });
    });

    it("muExportBasename neutralizes path separators in the basename", () => {
        const { wrapper } = mountArchives();
        const base = wrapper.vm.muExportBasename({
            page_path: "../../../secret/x.mu",
            hash: "abc",
        });
        expect(base.includes("/")).toBe(false);
        expect(base.includes("..")).toBe(false);
    });

    it("onArchiveContentClick routes nomadnet links and scrolls fragment anchors", () => {
        const { wrapper, routerPush } = mountArchives();
        const holder = document.createElement("div");
        holder.innerHTML =
            '<a class="nomadnet-link" data-nomadnet-url="abc123:/p.mu`q=1">n</a>' +
            '<div id="frag ment">target</div><a href="#frag%20ment">f</a>';
        document.body.appendChild(holder);
        try {
            const nomadA = holder.querySelector("a.nomadnet-link");
            const fragTarget = holder.querySelector("#frag\\ ment");
            fragTarget.scrollIntoView = vi.fn();
            const fragA = holder.querySelector('a[href^="#"]');
            const clickOn = (el) => {
                const ev = new MouseEvent("click", { bubbles: true, cancelable: true });
                Object.defineProperty(ev, "target", { value: el });
                wrapper.vm.onArchiveContentClick(ev);
                return ev;
            };
            const nomadEv = clickOn(nomadA);
            expect(routerPush).toHaveBeenCalledWith({
                name: "nomadnetwork",
                params: { destinationHash: "abc123" },
                query: { path: "/p.mu`q=1" },
            });
            expect(nomadEv.defaultPrevented).toBe(true);
            routerPush.mockClear();
            const fragEv = clickOn(fragA);
            expect(fragEv.defaultPrevented).toBe(true);
            expect(fragTarget.scrollIntoView).toHaveBeenCalled();
        } finally {
            document.body.removeChild(holder);
        }
        const noop = document.createElement("div");
        const noopEv = new MouseEvent("click");
        Object.defineProperty(noopEv, "target", { value: noop });
        expect(() => wrapper.vm.onArchiveContentClick(noopEv)).not.toThrow();
    });

    it("onArchiveContentClick opens http links externally", async () => {
        const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
        const { wrapper } = mountArchives();
        const holder = document.createElement("div");
        holder.innerHTML = '<a href="https://example.com/page">Example</a>';
        document.body.appendChild(holder);
        try {
            const link = holder.querySelector("a");
            const ev = new MouseEvent("click", { bubbles: true, cancelable: true });
            Object.defineProperty(ev, "target", { value: link });
            wrapper.vm.onArchiveContentClick(ev);
            expect(openSpy).toHaveBeenCalledWith("https://example.com/page", "_blank", "noopener,noreferrer");
            expect(ev.defaultPrevented).toBe(true);
        } finally {
            document.body.removeChild(holder);
            openSpy.mockRestore();
        }
    });

    it("onArchiveContentClick blocks javascript: anchors without opening a window", () => {
        const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
        const { wrapper, routerPush } = mountArchives();
        const holder = document.createElement("div");
        holder.innerHTML = '<a href="javascript:alert(1)">bad</a>';
        document.body.appendChild(holder);
        try {
            const link = holder.querySelector("a");
            const ev = new MouseEvent("click", { bubbles: true, cancelable: true });
            Object.defineProperty(ev, "target", { value: link });
            wrapper.vm.onArchiveContentClick(ev);
            expect(ev.defaultPrevented).toBe(true);
            expect(openSpy).not.toHaveBeenCalled();
            expect(routerPush).not.toHaveBeenCalled();
        } finally {
            document.body.removeChild(holder);
            openSpy.mockRestore();
        }
    });
});
