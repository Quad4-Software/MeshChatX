import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import TranslatorPage from "@/components/translator/TranslatorPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

describe("TranslatorPage.vue", () => {
    let apiMock;

    beforeEach(() => {
        apiMock = {
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
        };
        window.api = apiMock;

        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({
                    data: {
                        packs: [
                            { pair: "enes", from: "en", to: "es", size: 1024 },
                            { pair: "deen", from: "de", to: "en", size: 2048 },
                        ],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountTranslatorPage = () => {
        const globals = mountToolsPageGlobals();
        globals.stubs.RouterLink = true;
        return mount(TranslatorPage, {
            global: globals,
        });
    };

    it("renders the translator page", async () => {
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBeGreaterThan(0));
        expect(wrapper.text()).toContain("Translator");
    });

    it("lists installed packs", async () => {
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBeGreaterThan(0));
        expect(wrapper.text()).toContain("English");
        expect(wrapper.text()).toContain("Spanish");
    });

    it("swaps languages", async () => {
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBeGreaterThan(0));
        await wrapper.setData({ sourceLang: "en", targetLang: "es" });
        const swapButton = wrapper.findAll("button").find((b) => b.attributes("title")?.includes("Swap"));
        expect(swapButton).toBeDefined();
        await swapButton.trigger("click");
        expect(wrapper.vm.sourceLang).toBe("es");
        expect(wrapper.vm.targetLang).toBe("en");
    });

    it("disables translate when source and target are the same", async () => {
        const wrapper = mountTranslatorPage();
        await wrapper.setData({ sourceLang: "en", targetLang: "en", inputText: "hello" });
        expect(wrapper.vm.canTranslate).toBe(false);
    });

    it("loads the catalog and marks installed pairs", async () => {
        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/catalog")) {
                return Promise.resolve({
                    data: {
                        pairs: [
                            { pair: "enes", from: "en", to: "es", architecture: "base", size: 1024 },
                            { pair: "fren", from: "fr", to: "en", architecture: "tiny", size: 2048 },
                        ],
                    },
                });
            }
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({
                    data: { packs: [{ pair: "enes", from: "en", to: "es", size: 1024 }] },
                });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBeGreaterThan(0));

        const toggle = wrapper.findAll("button").find((b) => b.text() === "Download packs");
        expect(toggle).toBeDefined();
        await toggle.trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.catalogPairs.length).toBe(2));

        expect(wrapper.text()).toContain("Installed");
        const downloadButtons = wrapper.findAll("button").filter((b) => b.text() === "Download");
        expect(downloadButtons.length).toBe(1);
    });

    it("downloads a catalog pair and reloads packs", async () => {
        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/catalog")) {
                return Promise.resolve({
                    data: {
                        pairs: [{ pair: "fren", from: "fr", to: "en", architecture: "tiny", size: 2048 }],
                    },
                });
            }
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({ data: { packs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        apiMock.post.mockImplementation((url, body) => {
            if (url.includes("/api/v1/translation/packs/fetch")) {
                expect(body).toEqual({ pair: "fren" });
                return Promise.resolve({ data: { installed: ["fren"], failed: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBe(0));

        const toggle = wrapper.findAll("button").find((b) => b.text() === "Download packs");
        await toggle.trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.catalogPairs.length).toBe(1));

        const download = wrapper.findAll("button").find((b) => b.text() === "Download");
        await download.trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.isDownloading("fren")).toBe(false));
        const [url, body] = apiMock.post.mock.calls[0];
        expect(url).toContain("/translation/packs/fetch");
        expect(body).toEqual({ pair: "fren" });
    });

    it("posts an all-pairs download", async () => {
        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/catalog")) {
                return Promise.resolve({
                    data: {
                        pairs: [{ pair: "fren", from: "fr", to: "en", architecture: "tiny", size: 2048 }],
                    },
                });
            }
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({ data: { packs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        apiMock.post.mockResolvedValue({ data: { installed: ["fren"], failed: [] } });
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBe(0));

        const toggle = wrapper.findAll("button").find((b) => b.text() === "Download packs");
        await toggle.trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.catalogPairs.length).toBe(1));

        const all = wrapper.findAll("button").find((b) => b.text() === "Download all");
        await all.trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.isDownloadingAll).toBe(false));
        const [url, body] = apiMock.post.mock.calls[0];
        expect(url).toContain("/translation/packs/fetch");
        expect(body).toEqual({ all: true });
    });

    it("merges both directions of a pair into one entry and downloads both", async () => {
        const postedPairs = [];
        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/catalog")) {
                return Promise.resolve({
                    data: {
                        pairs: [
                            { pair: "enru", from: "en", to: "ru", architecture: "base", size: 1024 },
                            { pair: "ruen", from: "ru", to: "en", architecture: "base", size: 1024 },
                            { pair: "fren", from: "fr", to: "en", architecture: "tiny", size: 2048 },
                        ],
                    },
                });
            }
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({ data: { packs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        apiMock.post.mockImplementation((url, body) => {
            if (url.includes("/api/v1/translation/packs/fetch")) {
                postedPairs.push(body);
                return Promise.resolve({ data: { installed: [body.pair], failed: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBe(0));

        const toggle = wrapper.findAll("button").find((b) => b.text() === "Download packs");
        await toggle.trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.catalogPairs.length).toBe(3));

        // Two directions collapse into one entry.
        expect(wrapper.vm.mergedCatalog.length).toBe(2);
        const merged = wrapper.vm.mergedCatalog.find((g) => g.directions.length === 2);
        expect(merged).toBeDefined();
        expect(wrapper.vm.groupLabel(merged)).toContain("<->");

        const downloadButtons = wrapper.findAll("button").filter((b) => b.text() === "Download");
        expect(downloadButtons.length).toBe(2);

        // One click downloads both directions.
        await wrapper.vm.downloadGroup(merged);
        await vi.waitFor(() => expect(postedPairs.length).toBe(2));
        expect(postedPairs).toContainEqual({ pair: "enru" });
        expect(postedPairs).toContainEqual({ pair: "ruen" });
    });

    it("filters the merged catalog with the search input", async () => {
        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/catalog")) {
                return Promise.resolve({
                    data: {
                        pairs: [
                            { pair: "enru", from: "en", to: "ru", architecture: "base", size: 1024 },
                            { pair: "ruen", from: "ru", to: "en", architecture: "base", size: 1024 },
                            { pair: "fren", from: "fr", to: "en", architecture: "tiny", size: 2048 },
                        ],
                    },
                });
            }
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({ data: { packs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBe(0));
        wrapper.vm.showCatalog = true;
        wrapper.vm.catalogPairs = await import("@/js/TranslationService.js").then((m) => m.fetchCatalog());
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.filteredCatalog.length).toBe(2);
        wrapper.vm.catalogSearch = "russian";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.filteredCatalog.length).toBe(1);
        wrapper.vm.catalogSearch = "fren";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.filteredCatalog.length).toBe(1);
        wrapper.vm.catalogSearch = "zzzz";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.filteredCatalog.length).toBe(0);
    });

    it("surfaces a catalog error when downloads are blocked", async () => {
        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/catalog")) {
                return Promise.reject(new Error("blocked"));
            }
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({ data: { packs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBe(0));

        const toggle = wrapper.findAll("button").find((b) => b.text() === "Download packs");
        await toggle.trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.catalogError).toBeTruthy());
        expect(wrapper.text()).toContain("Could not load the pack catalog");
    });

    it("hides the docs hint in the empty state and shows the catalog toggle", async () => {
        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({ data: { packs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBe(0));
        expect(wrapper.text()).toContain("No packs installed");
        expect(wrapper.text()).toContain("Download packs");
        expect(wrapper.text()).not.toContain("mozilla");
    });

    it("shows a message when no packs are installed", async () => {
        apiMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/translation/packs")) {
                return Promise.resolve({ data: { packs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.packs.length).toBe(0));
        expect(wrapper.text()).toContain("No packs installed");
    });
});
