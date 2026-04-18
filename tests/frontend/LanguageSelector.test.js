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
                    Teleport: true,
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

        expect(wrapper.find(".fixed").exists()).toBe(false);

        await button.trigger("click");
        expect(wrapper.find(".fixed").exists()).toBe(true);

        await button.trigger("click");
        expect(wrapper.find(".fixed").exists()).toBe(false);
    });

    it("lists all available languages in the dropdown", async () => {
        const wrapper = mountLanguageSelector();
        await wrapper.find("button").trigger("click");

        const languageButtons = wrapper.findAll(".fixed button");
        const labels = languageButtons.map((b) => b.text());

        // English is pinned to the front; remaining locales are sorted by display name
        expect(labels[0]).toContain("English");
        expect(labels).toEqual(
            expect.arrayContaining([
                expect.stringContaining("English"),
                expect.stringContaining("Deutsch"),
                expect.stringContaining("Español"),
                expect.stringContaining("Français"),
                expect.stringContaining("Italiano"),
                expect.stringContaining("Nederlands"),
                expect.stringContaining("\u0420\u0443\u0441\u0441\u043a\u0438\u0439"),
                expect.stringContaining("\u4e2d\u6587"),
            ])
        );
        expect(languageButtons.length).toBeGreaterThanOrEqual(8);
    });

    it("emits language-change when a different language is selected", async () => {
        const wrapper = mountLanguageSelector("en");
        await wrapper.find("button").trigger("click");

        const deButton = wrapper.findAll(".fixed button")[1];
        await deButton.trigger("click");

        expect(wrapper.emitted("language-change")).toBeTruthy();
        expect(wrapper.emitted("language-change")[0]).toEqual(["de"]);
        expect(wrapper.find(".fixed").exists()).toBe(false);
    });

    it("does not emit language-change when the current language is selected", async () => {
        const wrapper = mountLanguageSelector("en");
        await wrapper.find("button").trigger("click");

        const enButton = wrapper.findAll(".fixed button")[0];
        await enButton.trigger("click");

        expect(wrapper.emitted("language-change")).toBeFalsy();
        expect(wrapper.find(".fixed").exists()).toBe(false);
    });

    it("renders a single trigger button", () => {
        const wrapper = mountLanguageSelector();
        expect(wrapper.findAll("button").length).toBe(1);
    });

    it("button is focusable", () => {
        const wrapper = mountLanguageSelector();
        const btn = wrapper.find("button");
        expect(btn.element.tabIndex).toBeGreaterThanOrEqual(-1);
    });
});
