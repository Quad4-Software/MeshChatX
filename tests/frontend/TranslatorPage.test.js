import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import TranslatorPage from "@/components/translator/TranslatorPage.vue";

describe("TranslatorPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({ data: { config: { translator_enabled: true } } });
            }
            if (url === "/api/v1/translator/languages") {
                return Promise.resolve({
                    data: {
                        languages: [
                            { code: "en", name: "English", source: "argos" },
                            { code: "de", name: "German", source: "argos" },
                            { code: "en", name: "English", source: "libretranslate" },
                            { code: "de", name: "German", source: "libretranslate" },
                        ],
                        has_argos: true,
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
        return mount(TranslatorPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                    RouterLink: true,
                },
            },
        });
    };

    it("renders the translator page", async () => {
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.config).not.toBeNull());
        expect(wrapper.text()).toContain("Translator");
    });

    it("switches translation modes", async () => {
        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.config).not.toBeNull());

        const libreButton = wrapper.findAll("button").find((b) => b.text().includes("LibreTranslate"));
        await libreButton.trigger("click");
        expect(wrapper.vm.translationMode).toBe("libretranslate");
        expect(wrapper.text()).toContain("LibreTranslate API Server");

        const argosButton = wrapper.findAll("button").find((b) => b.text().includes("Argos Translate"));
        await argosButton.trigger("click");
        expect(wrapper.vm.translationMode).toBe("argos");
    });

    it("calls translate API and displays result", async () => {
        window.api.post = vi.fn().mockResolvedValue({
            data: {
                translated_text: "Hallo Welt",
                source_lang: "en",
                target_lang: "de",
            },
        });

        const wrapper = mountTranslatorPage();
        await vi.waitFor(() => expect(wrapper.vm.config).not.toBeNull());

        await wrapper.setData({
            inputText: "Hello World",
            sourceLang: "en",
            targetLang: "de",
        });

        await wrapper.vm.$nextTick();

        // Call directly to verify logic
        await wrapper.vm.translateText();

        expect(window.api.post).toHaveBeenCalledWith(
            "/api/v1/translator/translate",
            expect.objectContaining({
                text: "Hello World",
                source_lang: "en",
                target_lang: "de",
            })
        );

        await vi.waitFor(() => expect(wrapper.text()).toContain("Hallo Welt"));
    });

    it("swaps languages", async () => {
        const wrapper = mountTranslatorPage();
        await wrapper.setData({ sourceLang: "en", targetLang: "de" });

        const swapButton = wrapper.findAll("button").find((b) => b.text().includes("Swap"));
        await swapButton.trigger("click");

        expect(wrapper.vm.sourceLang).toBe("de");
        expect(wrapper.vm.targetLang).toBe("en");
    });
});
