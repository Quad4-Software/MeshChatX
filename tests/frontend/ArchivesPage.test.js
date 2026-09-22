// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ArchivesPage from "@/features/archives/ArchivesPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";
import {
    downloadTextAsFile,
    muExportFilename,
    muExportFilenameDisambiguated,
} from "@/features/archives/lib/archiveExport.ts";
import { cardPreviewHtml, renderFullContent } from "@/features/archives/lib/archiveRender.ts";

describe("ArchivesPage.svelte", () => {
    let createObjectURLSpy;
    let revokeObjectURLSpy;
    let api;

    beforeEach(() => {
        createObjectURLSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
        revokeObjectURLSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
        registerTranslator(null);
        registerFallbackMessages(en);
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
        cleanup();
        createObjectURLSpy.mockRestore();
        revokeObjectURLSpy.mockRestore();
        delete window.api;
    });

    it("renders translated archives title instead of raw key", async () => {
        render(ArchivesPage);
        expect(screen.getByText("Archives")).toBeTruthy();
        expect(screen.queryByText("nav.archives")).toBeNull();
        expect(screen.queryByText("archives.title")).toBeNull();
    });

    it("muExportFilename uses .mu extension from page path", () => {
        expect(
            muExportFilename({
                page_path: "/node/page.mu",
                hash: "abcdef",
            })
        ).toBe("page.mu");
        expect(
            muExportFilename({
                page_path: "/readme.txt",
                hash: "abcdef",
            })
        ).toBe("readme.txt");
    });

    it("muExportFilenameDisambiguated appends hash prefix", () => {
        expect(
            muExportFilenameDisambiguated({
                page_path: "/a.mu",
                hash: "1234567890ab",
            })
        ).toBe("a_12345678.mu");
        expect(
            muExportFilenameDisambiguated({
                page_path: "/notes.md",
                hash: "1234567890ab",
            })
        ).toBe("notes_12345678.md");
    });

    it("renderFullContent renders micron markup for .mu pages", () => {
        const out = renderFullContent(
            {
                page_path: "/page/index.mu",
                content: ">Hello micron",
                destination_hash: "aa".repeat(16),
                hash: "bb".repeat(16),
                id: 1,
            },
            {
                renderMarkdown: true,
                renderHtml: true,
                renderPlaintext: true,
                nomadDestinationHash: "aa".repeat(16),
                nomad_micron_wasm_use: false,
            },
            false
        );
        expect(out.toLowerCase()).not.toContain("<script");
        expect(out.length).toBeGreaterThan(0);
    });

    it("cardPreviewHtml uses preview content for micron cards", () => {
        const html = cardPreviewHtml(
            {
                id: 9,
                hash: "abcdef12",
                page_path: "/page/index.mu",
                preview: ">Card preview",
                destination_hash: "aa".repeat(16),
            },
            "",
            {},
            false,
            {
                renderMarkdown: true,
                renderHtml: true,
                renderPlaintext: true,
                nomadDestinationHash: "aa".repeat(16),
                nomad_micron_wasm_use: false,
            }
        );
        expect(html.length).toBeGreaterThan(0);
        expect(html.toLowerCase()).not.toContain("<script");
    });

    it("downloadTextAsFile creates a blob URL and revokes it after DownloadUtils delay", async () => {
        vi.useFakeTimers();
        try {
            const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
            await downloadTextAsFile("hello", "test.mu");
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
