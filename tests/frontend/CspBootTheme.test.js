import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "../..");
const INDEX_HTML = resolve(ROOT, "meshchatx/src/frontend/index.html");
const BOOT_THEME_JS = resolve(ROOT, "meshchatx/src/frontend/public/boot-theme.js");
const PUBLIC_DIR = resolve(ROOT, "meshchatx/src/frontend/public");

const INLINE_SCRIPT_RE = /<script(?![^>]*\bsrc\s*=)[^>]*>/gi;
const SCRIPT_SRC_RE = /<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["'][^>]*>/gi;

describe("main app CSP and boot theme", () => {
    beforeEach(() => {
        document.documentElement.className = "";
        delete document.documentElement.dataset.bootTheme;
        document.documentElement.style.colorScheme = "";
        window.localStorage.clear();
        delete window.MeshChatXAndroid;
    });

    afterEach(() => {
        document.documentElement.className = "";
        delete document.documentElement.dataset.bootTheme;
        document.documentElement.style.colorScheme = "";
        window.localStorage.clear();
        delete window.MeshChatXAndroid;
    });

    it("index.html has no inline scripts (main CSP forbids unsafe-inline)", () => {
        const html = readFileSync(INDEX_HTML, "utf8");
        const inline = [...html.matchAll(INLINE_SCRIPT_RE)].map((m) => m[0]);
        expect(inline).toEqual([]);
    });

    it("index.html loads boot-theme.js from public before the app module", () => {
        const html = readFileSync(INDEX_HTML, "utf8");
        expect(existsSync(BOOT_THEME_JS)).toBe(true);
        expect(html).toContain('src="/boot-theme.js"');
        const bootIdx = html.indexOf('src="/boot-theme.js"');
        const mainIdx = html.indexOf('src="main.js"');
        expect(bootIdx).toBeGreaterThan(-1);
        expect(mainIdx).toBeGreaterThan(bootIdx);
    });

    it("every classic script src in index.html resolves under public or is the vite entry", () => {
        const html = readFileSync(INDEX_HTML, "utf8");
        const srcs = [...html.matchAll(SCRIPT_SRC_RE)].map((m) => m[1]);
        expect(srcs.length).toBeGreaterThan(0);
        for (const src of srcs) {
            if (src === "main.js" || src.endsWith("/main.js")) {
                continue;
            }
            const rel = src.replace(/^\//, "");
            expect(existsSync(resolve(PUBLIC_DIR, rel)), `missing public asset for ${src}`).toBe(
                true,
            );
        }
    });

    it("boot-theme.js applies dark theme by default", () => {
        const code = readFileSync(BOOT_THEME_JS, "utf8");
        // eslint-disable-next-line no-new-func
        Function(code)();
        expect(document.documentElement.classList.contains("dark")).toBe(true);
        expect(document.documentElement.dataset.bootTheme).toBe("dark");
        expect(document.documentElement.style.colorScheme).toBe("dark");
    });

    it("boot-theme.js respects localStorage light theme", () => {
        window.localStorage.setItem("meshchatx_ui_theme", "light");
        const code = readFileSync(BOOT_THEME_JS, "utf8");
        // eslint-disable-next-line no-new-func
        Function(code)();
        expect(document.documentElement.classList.contains("dark")).toBe(false);
        expect(document.documentElement.dataset.bootTheme).toBe("light");
        expect(document.documentElement.style.colorScheme).toBe("light");
    });

    it("boot-theme.js prefers Android bridge theme over localStorage", () => {
        window.localStorage.setItem("meshchatx_ui_theme", "dark");
        window.MeshChatXAndroid = {
            getPreferredUiTheme: () => "light",
        };
        const code = readFileSync(BOOT_THEME_JS, "utf8");
        // eslint-disable-next-line no-new-func
        Function(code)();
        expect(document.documentElement.dataset.bootTheme).toBe("light");
        expect(document.documentElement.classList.contains("dark")).toBe(false);
    });
});
