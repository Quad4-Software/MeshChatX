import { readdirSync, readFileSync, statSync } from "fs";
import { join } from "path";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    injectMeshchatThemeVariables,
    MESHCHAT_THEME_VARIABLES_LIGHT,
    MESHCHAT_THEME_VARIABLES_DARK,
    tailwindSemanticColorExtend,
} from "../../meshchatx/src/frontend/theme/designTokens.js";
import { THEME_PRESETS } from "../../meshchatx/src/frontend/theme/themeEngine.js";

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
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-error"]).toBe("#b91c1c");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-info"]).toBe("#0369a1");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-success"]).toBe("#166534");
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-warning"]).toBe("#9a3412");
    });

    it("preserves legacy dark palette anchors", () => {
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-canvas"]).toBe("#09090b");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-surface"]).toBe("#09090b");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-accent"]).toBe("#60a5fa");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-action-primary"]).toBe("#2563eb");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-error"]).toBe("#f87171");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-info"]).toBe("#38bdf8");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-success"]).toBe("#34d399");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-warning"]).toBe("#fb923c");
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

describe("design token references", () => {
    const FRONTEND = join(process.cwd(), "meshchatx/src/frontend");
    const VAR_REF_RE = /var\((--mc-[a-z0-9-]+)/g;

    function definedTokenNames() {
        const names = new Set([
            ...Object.keys(MESHCHAT_THEME_VARIABLES_LIGHT),
            ...Object.keys(MESHCHAT_THEME_VARIABLES_DARK),
        ]);
        for (const preset of Object.values(THEME_PRESETS)) {
            for (const mode of ["light", "dark"]) {
                for (const key of Object.keys(preset[mode] || {})) {
                    names.add(key);
                }
            }
        }
        return names;
    }

    function walkSources(dir, out = []) {
        for (const name of readdirSync(dir)) {
            if (name === "node_modules" || name === "public" || name === "fonts") {
                continue;
            }
            const full = join(dir, name);
            if (statSync(full).isDirectory()) {
                walkSources(full, out);
                continue;
            }
            if (/\.(css|vue|js|html)$/.test(name)) {
                out.push(full);
            }
        }
        return out;
    }

    it("every var(--mc-*) reference resolves to a defined token", () => {
        const defined = definedTokenNames();
        const missing = [];
        for (const file of walkSources(FRONTEND)) {
            const source = readFileSync(file, "utf8");
            for (const match of source.matchAll(VAR_REF_RE)) {
                if (!defined.has(match[1])) {
                    missing.push(`${file}: ${match[1]}`);
                }
            }
        }
        expect([...new Set(missing)]).toEqual([]);
    });
});
