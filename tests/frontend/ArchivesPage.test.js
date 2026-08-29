// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ArchivesPage from "@/components/archives/ArchivesPage.vue";
import { createTestI18n } from "./testI18n.js";

describe("ArchivesPage.vue", () => {
    let createObjectURLSpy;
    let revokeObjectURLSpy;
    let api;

    beforeEach(() => {
        createObjectURLSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
        revokeObjectURLSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
        api = {
            get: vi.fn().mockResolvedValue({
                data: {
                    archives: [],
                    pagination: { page: 1, limit: 25, total_count: 0, total_pages: 0 },
                },
            }),
            post: vi.fn(),
            delete: vi.fn(),
        };
        window.api = api;
    });

    afterEach(() => {
        createObjectURLSpy.mockRestore();
        revokeObjectURLSpy.mockRestore();
    });

    const mountPage = () =>
        mount(ArchivesPage, {
            global: {
                plugins: [createTestI18n()],
                mocks: {
                    $route: { query: {} },
                    $router: { push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });

    it("renders translated archives title instead of raw key", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("Archives");
        expect(wrapper.text()).not.toContain("nav.archives");
        expect(wrapper.text()).not.toContain("archives.title");
    });

    it("muExportFilename uses .mu extension from page path", () => {
        const wrapper = mountPage();
        expect(
            wrapper.vm.muExportFilename({
                page_path: "/node/page.mu",
                hash: "abcdef",
            })
        ).toBe("page.mu");
        expect(
            wrapper.vm.muExportFilename({
                page_path: "/readme.txt",
                hash: "abcdef",
            })
        ).toBe("readme.txt");
    });

    it("muExportFilenameDisambiguated appends hash prefix", () => {
        const wrapper = mountPage();
        expect(
            wrapper.vm.muExportFilenameDisambiguated({
                page_path: "/a.mu",
                hash: "1234567890ab",
            })
        ).toBe("a_12345678.mu");
        expect(
            wrapper.vm.muExportFilenameDisambiguated({
                page_path: "/notes.md",
                hash: "1234567890ab",
            })
        ).toBe("notes_12345678.md");
    });

    it("renderFullContent renders micron markup for .mu pages", () => {
        const wrapper = mountPage();
        const out = wrapper.vm.renderFullContent({
            page_path: "/page/index.mu",
            content: ">Hello micron",
            destination_hash: "aa".repeat(16),
            hash: "bb".repeat(16),
            id: 1,
        });
        expect(out.toLowerCase()).not.toContain("<script");
        expect(out.length).toBeGreaterThan(0);
    });

    it("cardPreviewHtml uses preview content for micron cards", () => {
        const wrapper = mountPage();
        const html = wrapper.vm.cardPreviewHtml({
            id: 9,
            hash: "abcdef12",
            page_path: "/page/index.mu",
            preview: ">Card preview",
            destination_hash: "aa".repeat(16),
        });
        expect(html.length).toBeGreaterThan(0);
        expect(html.toLowerCase()).not.toContain("<script");
    });

    it("downloadTextAsFile creates a blob URL and revokes it after DownloadUtils delay", async () => {
        vi.useFakeTimers();
        try {
            const wrapper = mountPage();
            const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
            await wrapper.vm.downloadTextAsFile("hello", "test.mu");
            expect(createObjectURLSpy).toHaveBeenCalled();
            expect(clickSpy).toHaveBeenCalled();
            vi.advanceTimersByTime(10000);
            expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:mock");
            clickSpy.mockRestore();
        } finally {
            vi.useRealTimers();
        }
    });
});
