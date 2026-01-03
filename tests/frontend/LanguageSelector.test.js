import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import LanguageSelector from "@/components/LanguageSelector.vue";

describe("LanguageSelector.vue", () => {
    const mountLanguageSelector = (locale = "en") => {
        return mount(LanguageSelector, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $i18n: {
                        locale: locale,
                    },
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });
    };

    it("renders the language selector button", () => {
        const wrapper = mountLanguageSelector();
        expect(wrapper.find("button").exists()).toBe(true);
    });

    it("toggles the dropdown when the button is clicked", async () => {
        const wrapper = mountLanguageSelector();
        const button = wrapper.find("button");

        expect(wrapper.find(".absolute").exists()).toBe(false);

        await button.trigger("click");
        expect(wrapper.find(".absolute").exists()).toBe(true);

        await button.trigger("click");
        expect(wrapper.find(".absolute").exists()).toBe(false);
    });

    it("lists all available languages in the dropdown", async () => {
        const wrapper = mountLanguageSelector();
        await wrapper.find("button").trigger("click");

        const languageButtons = wrapper.findAll(".absolute button");
        expect(languageButtons).toHaveLength(3);
        expect(languageButtons[0].text()).toContain("English");
        expect(languageButtons[1].text()).toContain("Deutsch");
        expect(languageButtons[2].text()).toContain("Русский");
    });

    it("emits language-change when a different language is selected", async () => {
        const wrapper = mountLanguageSelector("en");
        await wrapper.find("button").trigger("click");

        const deButton = wrapper.findAll(".absolute button")[1];
        await deButton.trigger("click");

        expect(wrapper.emitted("language-change")).toBeTruthy();
        expect(wrapper.emitted("language-change")[0]).toEqual(["de"]);
        expect(wrapper.find(".absolute").exists()).toBe(false);
    });

    it("does not emit language-change when the current language is selected", async () => {
        const wrapper = mountLanguageSelector("en");
        await wrapper.find("button").trigger("click");

        const enButton = wrapper.findAll(".absolute button")[0];
        await enButton.trigger("click");

        expect(wrapper.emitted("language-change")).toBeFalsy();
        expect(wrapper.find(".absolute").exists()).toBe(false);
    });
});
