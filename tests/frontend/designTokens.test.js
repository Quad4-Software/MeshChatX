import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    injectMeshchatThemeVariables,
    vuetifyThemesFromTokens,
    MESHCHAT_THEME_VARIABLES_LIGHT,
    MESHCHAT_THEME_VARIABLES_DARK,
    tailwindSemanticColorExtend,
} from "../../meshchatx/src/frontend/theme/designTokens.js";

describe("design tokens", () => {
    it("light and dark variable maps define the same keys", () => {
        expect(Object.keys(MESHCHAT_THEME_VARIABLES_LIGHT).sort()).toEqual(
            Object.keys(MESHCHAT_THEME_VARIABLES_DARK).sort()
        );
    });

    it("preserves legacy light palette anchors", () => {
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-canvas"]).toBe("#f8fafc");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-surface"]).toBe("#ffffff");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-accent"]).toBe("#2563eb");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-action-primary"]).toBe("#2563eb");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-error"]).toBe("#dc2626");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-info"]).toBe("#0284c7");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-success"]).toBe("#16a34a");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-warning"]).toBe("#f97316");
    });

    it("preserves legacy dark palette anchors", () => {
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-canvas"]).toBe("#09090b");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-surface"]).toBe("#18181b");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-accent"]).toBe("#60a5fa");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-action-primary"]).toBe("#2563eb");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-error"]).toBe("#f87171");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-info"]).toBe("#38bdf8");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-success"]).toBe("#34d399");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-warning"]).toBe("#fb923c");
    });

    it("vuetifyThemesFromTokens tracks CSS canvas/surface/accent and status colors", () => {
        const t = vuetifyThemesFromTokens();
        expect(t.light.colors.background).toBe(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-canvas"]);
        expect(t.light.colors.surface).toBe(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-surface"]);
        expect(t.light.colors.primary).toBe(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-action-primary"]);
        expect(t.light.colors.error).toBe(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-error"]);
        expect(t.dark.colors.background).toBe(MESHCHAT_THEME_VARIABLES_DARK["--mc-canvas"]);
        expect(t.dark.colors.surface).toBe(MESHCHAT_THEME_VARIABLES_DARK["--mc-surface"]);
        expect(t.dark.colors.primary).toBe(MESHCHAT_THEME_VARIABLES_DARK["--mc-action-primary"]);
        expect(t.dark.colors.error).toBe(MESHCHAT_THEME_VARIABLES_DARK["--mc-error"]);
    });

    it("tailwindSemanticColorExtend uses var() for every semantic color", () => {
        const sem = tailwindSemanticColorExtend();
        for (const v of Object.values(sem)) {
            expect(v).toMatch(/^var\(--mc-/);
        }
    });
});

describe("injectMeshchatThemeVariables", () => {
    beforeEach(() => {
        document.getElementById("meshchat-design-tokens")?.remove();
    });

    afterEach(() => {
        document.getElementById("meshchat-design-tokens")?.remove();
    });

    it("injects :root and .dark blocks with expected canvas values", () => {
        injectMeshchatThemeVariables(document);
        const el = document.getElementById("meshchat-design-tokens");
        expect(el).toBeTruthy();
        const text = el.textContent;
        expect(text).toContain(":root");
        expect(text).toContain(".dark");
        expect(text).toContain("--mc-canvas: #f8fafc");
        expect(text).toContain("--mc-canvas: #09090b");
    });

    it("is idempotent", () => {
        injectMeshchatThemeVariables(document);
        injectMeshchatThemeVariables(document);
        expect(document.querySelectorAll("#meshchat-design-tokens").length).toBe(1);
    });
});
