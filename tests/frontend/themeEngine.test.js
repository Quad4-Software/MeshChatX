import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    THEME_PRESET_IDS,
    THEME_PRESETS,
    accentDerivativeVars,
    applyAppearanceTheme,
    customThemeColorOverrides,
    buildThemeVariableOverrides,
    injectThemeOverrideVariables,
    normalizeOptionalHexColor,
    normalizeThemePreference,
    normalizeThemePreset,
    resolveCanvasColor,
    resolveEffectiveTheme,
    sanitizeThemeConfigFields,
    shellCanvasBackgroundStyle,
    updateThemeColorMeta,
    getThemePresetPreviewColors,
    themePresetPreviewStripStyle,
} from "../../meshchatx/src/frontend/theme/themeEngine.js";

describe("themeEngine", () => {
    it("normalizes theme preference and preset ids", () => {
        expect(normalizeThemePreference("dark")).toBe("dark");
        expect(normalizeThemePreference("system")).toBe("system");
        expect(normalizeThemePreference("weird")).toBe("light");
        expect(normalizeThemePreset("oled")).toBe("oled");
        expect(normalizeThemePreset("nope")).toBe("default");
        expect(THEME_PRESET_IDS).toContain("custom");
    });

    it("resolves effective theme including system preference", () => {
        expect(resolveEffectiveTheme("light", true)).toBe("light");
        expect(resolveEffectiveTheme("dark", false)).toBe("dark");
        expect(resolveEffectiveTheme("system", true)).toBe("dark");
        expect(resolveEffectiveTheme("system", false)).toBe("light");
    });

    it("builds preset and accent overrides", () => {
        const solarizedDark = buildThemeVariableOverrides({ theme_preset: "solarized" }, "dark");
        expect(solarizedDark["--mc-canvas"]).toBe("#002b36");

        const nordLight = buildThemeVariableOverrides({ theme_preset: "nord" }, "light");
        expect(nordLight["--mc-canvas"]).toBe("#eceff4");
        const gruvboxDark = buildThemeVariableOverrides({ theme_preset: "gruvbox" }, "dark");
        expect(gruvboxDark["--mc-canvas"]).toBe("#282828");
        const tokyoLight = buildThemeVariableOverrides({ theme_preset: "tokyo" }, "light");
        expect(tokyoLight["--mc-accent"]).toBe("#295cdb");
        const neoBrutalistDark = buildThemeVariableOverrides({ theme_preset: "neo_brutalist" }, "dark");
        expect(neoBrutalistDark["--mc-canvas"]).toBe("#18191b");
        expect(neoBrutalistDark["--mc-accent"]).toBe("#bc86dd");
        const neoBrutalistLight = buildThemeVariableOverrides({ theme_preset: "neo_brutalist" }, "light");
        expect(neoBrutalistLight["--mc-canvas"]).toBe("#f7f7f5");
        expect(neoBrutalistLight["--mc-accent"]).toBe("#8080c0");
        expect(normalizeThemePreset("hister")).toBe("neo_brutalist");

        const accent = buildThemeVariableOverrides({ accent_color: "#ff0000" }, "light");
        expect(accent["--mc-action-primary"]).toBe("#ff0000");
        expect(accentDerivativeVars("#ff0000", true)["--mc-accent"]).not.toBe("#ff0000");
    });

    it("applies custom canvas and surface colors only for custom preset", () => {
        const custom = buildThemeVariableOverrides(
            {
                theme_preset: "custom",
                custom_canvas_color: "#111111",
                custom_surface_color: "#222222",
            },
            "dark"
        );
        expect(custom["--mc-canvas"]).toBe("#111111");
        expect(custom["--mc-surface"]).toBe("#222222");
        expect(custom["--mc-border"]).toBeTruthy();

        const same = buildThemeVariableOverrides(
            {
                theme_preset: "custom",
                custom_canvas_color: "#222222",
                custom_surface_color: "#222222",
            },
            "dark"
        );
        expect(same["--mc-canvas"]).toBe("#222222");
        expect(same["--mc-surface"]).not.toBe("#222222");
        expect(customThemeColorOverrides("#222222", "#222222", "light")["--mc-surface"]).not.toBe("#222222");

        const ignored = buildThemeVariableOverrides(
            {
                theme_preset: "default",
                custom_canvas_color: "#111111",
            },
            "dark"
        );
        expect(ignored["--mc-canvas"]).toBeUndefined();
    });

    it("sanitizes optional theme color fields", () => {
        const config = {
            theme: "system",
            theme_preset: "oled",
            accent_color: "#abc",
            custom_canvas_color: "#123456",
            custom_surface_color: "bad",
        };
        sanitizeThemeConfigFields(config);
        expect(config.theme).toBe("system");
        expect(config.theme_preset).toBe("oled");
        expect(config.accent_color).toBeNull();
        expect(config.custom_canvas_color).toBe("#123456");
        expect(config.custom_surface_color).toBeNull();
        expect(normalizeOptionalHexColor("#aabbcc")).toBe("#aabbcc");
    });

    it("computes shell canvas background from resolved canvas color", () => {
        const style = shellCanvasBackgroundStyle({ ui_transparency: 0, theme_preset: "oled", theme: "dark" }, "dark");
        expect(style).toMatch(/^rgba\(0, 0, 0,/);
        expect(resolveCanvasColor({ theme_preset: "default" }, "light")).toBe("#f8fafc");
    });

    it("preset maps stay aligned for light and dark", () => {
        for (const id of THEME_PRESET_IDS) {
            expect(THEME_PRESETS[id].light).toBeTruthy();
            expect(THEME_PRESETS[id].dark).toBeTruthy();
        }
    });

    it("builds striped preview colors and gradient for presets", () => {
        const colors = getThemePresetPreviewColors({ theme_preset: "nord" }, "dark");
        expect(colors.canvas).toBe("#2e3440");
        expect(colors.accent).toBe("#81a1c1");
        const gradient = themePresetPreviewStripStyle(colors);
        expect(gradient).toContain("linear-gradient(to right");
        expect(gradient).toContain(colors.canvas);
        expect(gradient).toContain(colors.accent);
    });

    it("preview colors differ between presets in dark mode", () => {
        const solarized = getThemePresetPreviewColors({ theme_preset: "solarized", theme: "dark" }, "dark");
        const gruvbox = getThemePresetPreviewColors({ theme_preset: "gruvbox", theme: "dark" }, "dark");
        const dracula = getThemePresetPreviewColors({ theme_preset: "dracula", theme: "dark" }, "dark");
        expect(solarized.accent).not.toBe(gruvbox.accent);
        expect(gruvbox.accent).not.toBe(dracula.accent);
        expect(solarized.canvas).not.toBe(dracula.canvas);
    });
});

describe("applyAppearanceTheme DOM integration", () => {
    beforeEach(() => {
        document.documentElement.className = "";
        document.documentElement.removeAttribute("data-boot-theme");
        document.documentElement.removeAttribute("data-theme-preference");
        document.documentElement.style.colorScheme = "";
        document.getElementById("meshchat-theme-overrides")?.remove();
        document.getElementById("meshchat-theme-color-meta")?.remove();
        window.localStorage.clear();
    });

    afterEach(() => {
        document.documentElement.className = "";
        document.getElementById("meshchat-theme-overrides")?.remove();
        document.getElementById("meshchat-theme-color-meta")?.remove();
        window.localStorage.clear();
    });

    it("applies dark class, overrides, meta theme-color, and localStorage", () => {
        const result = applyAppearanceTheme(
            {
                theme: "dark",
                theme_preset: "oled",
            },
            { prefersDark: false }
        );
        expect(result.effectiveMode).toBe("dark");
        expect(document.documentElement.classList.contains("dark")).toBe(true);
        expect(document.documentElement.dataset.themePreference).toBe("dark");
        expect(window.localStorage.getItem("meshchatx_ui_theme")).toBe("dark");

        const override = document.getElementById("meshchat-theme-overrides");
        expect(override?.textContent).toContain("--mc-canvas: #000000");

        updateThemeColorMeta(document, "#000000");
        const meta = document.querySelector('meta[name="theme-color"]');
        expect(meta?.getAttribute("content")).toBe("#000000");
    });

    it("stores system preference and resolves from prefersDark", () => {
        applyAppearanceTheme({ theme: "system", theme_preset: "default" }, { prefersDark: true });
        expect(document.documentElement.classList.contains("dark")).toBe(true);
        expect(window.localStorage.getItem("meshchatx_ui_theme")).toBe("system");
    });

    it("injectThemeOverrideVariables targets active mode selector", () => {
        injectThemeOverrideVariables(document, { "--mc-accent": "#ff00ff" }, "light");
        const el = document.getElementById("meshchat-theme-overrides");
        expect(el?.textContent).toContain(":root");
        expect(el?.textContent).not.toContain(".dark");
    });
});
