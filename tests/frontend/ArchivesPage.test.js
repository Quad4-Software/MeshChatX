import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ArchivesPage from "@/components/archives/ArchivesPage.vue";

describe("ArchivesPage.vue", () => {
    let createObjectURLSpy;
    let revokeObjectURLSpy;

    beforeEach(() => {
        createObjectURLSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
        revokeObjectURLSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    });

    afterEach(() => {
        createObjectURLSpy.mockRestore();
        revokeObjectURLSpy.mockRestore();
    });

    const mountPage = () =>
        mount(ArchivesPage, {
            global: {
                mocks: {
                    $t: (key, params) => {
                        if (key === "archives.export_selected_mu") return `Export .mu (${params.count})`;
                        if (key === "archives.export_mu") return "Export .mu";
                        return key;
                    },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    ArchiveSidebar: true,
                },
            },
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

    it("downloadTextAsFile creates a blob URL and revokes it", () => {
        const wrapper = mountPage();
        const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
        wrapper.vm.downloadTextAsFile("hello", "test.mu");
        expect(createObjectURLSpy).toHaveBeenCalled();
        expect(clickSpy).toHaveBeenCalled();
        expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:mock");
        clickSpy.mockRestore();
    });
});
