// SPDX-License-Identifier: 0BSD

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/svelte";
import MicronEditorPage from "@/features/micron-editor/MicronEditorPage.svelte";
import { micronStorage } from "@/js/MicronStorage";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    createDefaultTab,
    createGuideTab,
    getDefaultContent,
    getGuideContent,
} from "@/features/micron-editor/lib/defaultContent.ts";
import {
    ensureNodeRunning,
    fetchNodePagesList,
    fetchPageNodesList,
    isUnsetMicronTabName,
    nomadPagePathForName,
    openNomadDestinationUrl,
    pageBaseWithExtension,
    pageNamesFromList,
    resolvePublishPageBase,
    tabNameToPageBase,
} from "@/features/micron-editor/lib/micronPublish.ts";

vi.mock("@/js/MicronStorage", () => ({
    micronStorage: {
        loadTabs: vi.fn().mockResolvedValue([]),
        saveTabs: vi.fn().mockResolvedValue(),
        clearAll: vi.fn().mockResolvedValue(),
    },
}));

vi.mock("@/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
        alert: vi.fn(),
        prompt: vi.fn().mockResolvedValue("test_page"),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

describe("defaultContent", () => {
    beforeEach(() => {
        registerFallbackMessages({
            tools: {
                micron_editor: {
                    main_tab: "Main",
                    guide_tab: "Quick Guide",
                },
            },
        });
    });

    it("generates default and guide tabs", () => {
        expect(getDefaultContent()).toContain("Welcome to Micron Editor");
        expect(getGuideContent()).toContain("Nomad Network supports a simple and functional markup language");
        const defaultTab = createDefaultTab();
        expect(defaultTab.name).toBe("Main");
        const guideTab = createGuideTab(42);
        expect(guideTab.id).toBe(42);
        expect(guideTab.name).toBe("Quick Guide");
    });
});

describe("micronPublish utilities", () => {
    beforeEach(() => {
        registerFallbackMessages({
            tools: {
                micron_editor: {
                    new_tab: "New Tab",
                },
            },
        });
    });

    it("extracts page names from list", () => {
        expect(pageNamesFromList(["index.mu", { name: "about.mu" }, null])).toEqual(["index.mu", "about.mu"]);
    });

    it("extracts base page name from tab name", () => {
        expect(tabNameToPageBase({ id: 1, name: "my_page.mu", content: "" })).toBe("my_page");
        expect(tabNameToPageBase({ id: 1, name: "docs.html", content: "" })).toBe("docs");
    });

    it("appends extension when needed", () => {
        expect(pageBaseWithExtension("page", { id: 1, name: "test.mu", content: "" })).toBe("page.mu");
        expect(pageBaseWithExtension("page.html")).toBe("page.html");
    });

    it("identifies unset tab names", () => {
        expect(isUnsetMicronTabName("")).toBe(true);
        expect(isUnsetMicronTabName("New Tab")).toBe(true);
        expect(isUnsetMicronTabName("New Tab 2")).toBe(true);
        expect(isUnsetMicronTabName("custom_name")).toBe(false);
    });

    it("normalizes nomad page paths", () => {
        expect(nomadPagePathForName("index.mu")).toBe("/page/index.mu");
        expect(nomadPagePathForName("/page/about.mu")).toBe("/page/about.mu");
        expect(nomadPagePathForName("/custom.mu")).toBe("/custom.mu");
    });

    it("handles page nodes APIs", async () => {
        window.api = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/page-nodes") {
                    return { data: [{ node_id: "node1", name: "Node 1", running: true }] };
                }
                if (url.includes("/pages")) {
                    return { data: { pages: ["index.mu"] } };
                }
                return { data: {} };
            }),
            post: vi.fn(async () => ({ data: { destination_hash: "abcd" } })),
        };

        const nodes = await fetchPageNodesList();
        expect(nodes).toHaveLength(1);

        const pages = await fetchNodePagesList("node1");
        expect(pages).toEqual(["index.mu"]);

        const started = await ensureNodeRunning({
            node_id: "node2",
            name: "Node 2",
            running: false,
        });
        expect(started.running).toBe(true);
    });

    it("parses nomad destination urls", () => {
        const onNavigate = vi.fn();
        openNomadDestinationUrl("nomadnetwork://aabbccddeeff00112233445566778899:/page/about.mu", onNavigate);
        expect(onNavigate).toHaveBeenCalledWith({
            destinationHash: "aabbccddeeff00112233445566778899",
            path: "/page/about.mu",
        });
    });
});

describe("MicronEditorPage.svelte component", () => {
    beforeEach(() => {
        cleanup();
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            tools: {
                micron_editor: {
                    title: "Micron Editor",
                    description: "Edit and preview Micron pages",
                    new_tab: "New Tab",
                    main_tab: "Main",
                    save: "Save",
                    reset: "Reset",
                    publish: "Publish",
                    view_preview: "Preview",
                    edit: "Edit",
                    publish_to_mesh_server: "Publish to Mesh Server",
                    placeholder: "Enter Micron markup here...",
                },
            },
        });
        window.api = {
            get: vi.fn(async () => ({ data: [] })),
            post: vi.fn(async () => ({ data: {} })),
            patch: vi.fn(async () => ({ data: {} })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    afterEach(() => {
        cleanup();
    });

    it("mounts and renders tabs", async () => {
        const { getByTestId } = render(MicronEditorPage);
        await waitFor(() => {
            expect(getByTestId("micron-editor-page")).toBeTruthy();
            expect(micronStorage.loadTabs).toHaveBeenCalled();
        });
    });
});
