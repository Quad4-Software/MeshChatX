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
                    ArchiveSidebar: true,
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
        }
    });

    it("archiveViewerClasses stays an array for adversarial page_path values", () => {
        const { wrapper } = mountArchives();
        for (const page_path of nastyPaths) {
            wrapper.vm.viewingArchive = { page_path };
            expect(Array.isArray(wrapper.vm.archiveViewerClasses)).toBe(true);
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

    it("onArchiveContentClick handles nomadnet links and fragment anchors without throwing", () => {
        const { wrapper, routerPush } = mountArchives();
        const holder = document.createElement("div");
        holder.innerHTML =
            '<a class="nomadnet-link" data-nomadnet-url="abc123:/p.mu`q=1">n</a>' + '<a href="#frag%20ment">f</a>';
        document.body.appendChild(holder);
        try {
            const nomadA = holder.querySelector("a.nomadnet-link");
            const fragA = holder.querySelector('a[href^="#"]');
            const clickOn = (el) => {
                const ev = new MouseEvent("click", { bubbles: true });
                Object.defineProperty(ev, "target", { value: el });
                wrapper.vm.onArchiveContentClick(ev);
            };
            clickOn(nomadA);
            expect(routerPush).toHaveBeenCalledWith({
                name: "nomadnetwork",
                params: { destinationHash: "abc123" },
                query: { path: "/p.mu`q=1" },
            });
            routerPush.mockClear();
            clickOn(fragA);
        } finally {
            document.body.removeChild(holder);
        }
        const noop = document.createElement("div");
        const noopEv = new MouseEvent("click");
        Object.defineProperty(noopEv, "target", { value: noop });
        expect(() => wrapper.vm.onArchiveContentClick(noopEv)).not.toThrow();
    });
});
