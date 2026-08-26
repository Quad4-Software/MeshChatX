import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import ThemePresetPicker from "../../meshchatx/src/frontend/components/settings/ThemePresetPicker.vue";
import { THEME_PRESET_CATALOG } from "../../meshchatx/src/frontend/theme/themeEngine.js";

describe("ThemePresetPicker", () => {
    it("lists every theme preset in the select and preview grid", () => {
        const wrapper = mount(ThemePresetPicker, {
            props: {
                value: "default",
                config: { theme: "light", theme_preset: "default" },
            },
            global: {
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: { template: "<span />" },
                },
            },
        });

        expect(wrapper.findAll("select option").length).toBe(THEME_PRESET_CATALOG.length);
        expect(wrapper.findAll('[role="option"]').length).toBe(THEME_PRESET_CATALOG.length);
        expect(wrapper.findAll(".theme-preset-swatch").length).toBe(THEME_PRESET_CATALOG.length + 1);
    });

    it("emits change when a grid preset is clicked", async () => {
        const wrapper = mount(ThemePresetPicker, {
            props: {
                value: "default",
                config: { theme: "light", theme_preset: "default" },
            },
            global: {
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: { template: "<span />" },
                },
            },
        });

        const gridButtons = wrapper.findAll('[role="option"]');
        await gridButtons[2].trigger("click");
        expect(wrapper.emitted("change")?.[0]?.[0]).toBe(THEME_PRESET_CATALOG[2].id);
    });

    it("grid swatches ignore user accent when previewing other presets", async () => {
        const wrapper = mount(ThemePresetPicker, {
            props: {
                value: "default",
                config: {
                    theme: "dark",
                    theme_preset: "default",
                    accent_color: "#ff00ff",
                },
            },
            global: {
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: { template: "<span />" },
                },
            },
        });

        const solarizedButton = wrapper.findAll('[role="option"]')[3];
        const nordButton = wrapper.findAll('[role="option"]')[4];
        const solarizedAccent = solarizedButton.findAll(".theme-preset-swatch__band")[2].element.style.backgroundColor;
        const nordAccent = nordButton.findAll(".theme-preset-swatch__band")[2].element.style.backgroundColor;
        expect(solarizedAccent).not.toBe("rgb(255, 0, 255)");
        expect(nordAccent).not.toBe("rgb(255, 0, 255)");
        expect(solarizedAccent).not.toBe(nordAccent);
    });
});
