// SPDX-License-Identifier: 0BSD

import { render, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi } from "vitest";
import ThemePresetPicker from "../../meshchatx/src/frontend/features/settings/components/ThemePresetPicker.svelte";
import { THEME_PRESET_CATALOG } from "../../meshchatx/src/frontend/theme/themeEngine.js";

describe("ThemePresetPicker", () => {
    it("lists every theme preset in the select and preview grid", () => {
        const { container } = render(ThemePresetPicker, {
            props: {
                value: "default",
                config: { theme: "light", theme_preset: "default" },
            },
        });

        expect(container.querySelectorAll("select option").length).toBe(THEME_PRESET_CATALOG.length);
        expect(container.querySelectorAll('[role="option"]').length).toBe(THEME_PRESET_CATALOG.length);
        expect(container.querySelectorAll(".theme-preset-swatch").length).toBe(THEME_PRESET_CATALOG.length + 1);
    });

    it("emits change when a grid preset is clicked", async () => {
        const onchange = vi.fn();
        const { container } = render(ThemePresetPicker, {
            props: {
                value: "default",
                config: { theme: "light", theme_preset: "default" },
                onchange,
            },
        });

        const gridButtons = container.querySelectorAll('[role="option"]');
        await fireEvent.click(gridButtons[2]);
        expect(onchange).toHaveBeenCalledWith(THEME_PRESET_CATALOG[2].id);
    });

    it("grid swatches ignore user accent when previewing other presets", async () => {
        const { container } = render(ThemePresetPicker, {
            props: {
                value: "default",
                config: {
                    theme: "dark",
                    theme_preset: "default",
                    accent_color: "#ff00ff",
                },
            },
        });

        const solarizedButton = container.querySelectorAll('[role="option"]')[3];
        const nordButton = container.querySelectorAll('[role="option"]')[4];
        const solarizedAccent = solarizedButton.querySelectorAll(".theme-preset-swatch__band")[2].style.backgroundColor;
        const nordAccent = nordButton.querySelectorAll(".theme-preset-swatch__band")[2].style.backgroundColor;
        expect(solarizedAccent).not.toBe("rgb(255, 0, 255)");
        expect(nordAccent).not.toBe("rgb(255, 0, 255)");
        expect(solarizedAccent).not.toBe(nordAccent);
    });
});
