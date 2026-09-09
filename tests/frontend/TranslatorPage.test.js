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
