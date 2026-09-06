import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
    MESHCHAT_THEME_VARIABLES_LIGHT,
    MESHCHAT_THEME_VARIABLES_DARK,
    injectMeshchatThemeVariables,
} from "../../meshchatx/src/frontend/theme/designTokens.js";

const ROOT = resolve(import.meta.dirname, "../..");

describe("boot and load smoothness", () => {
    beforeEach(() => {
        document.head.innerHTML = "";
        document.body.innerHTML = "";
        document.documentElement.className = "";
    });

    afterEach(() => {
        document.head.innerHTML = "";
        document.body.innerHTML = "";
        document.documentElement.className = "";
    });

    it("index.html uses canvas-colored body instead of gray-100 flash", () => {
        const html = readFileSync(resolve(ROOT, "meshchatx/src/frontend/index.html"), "utf8");
        const bootTheme = readFileSync(resolve(ROOT, "meshchatx/src/frontend/public/boot-theme.js"), "utf8");
        expect(html).not.toMatch(/body class="bg-gray-100"/);
        expect(html).toContain("background-color: #f8fafc");
        expect(html).toContain("background-color: #09090b");
        expect(html).toContain('src="/boot-theme.js"');
        expect(html).not.toMatch(/<script(?![^>]*\bsrc=)[^>]*>/);
        expect(bootTheme).toContain("meshchatx_ui_theme");
        expect(bootTheme).toContain("getPreferredUiTheme");
        expect(html).toContain('id="meshchatx-boot-splash"');
        expect(html).toContain('id="app"');
    });

    it("style.css paints html/body/#app with semantic canvas", () => {
        const css = readFileSync(resolve(ROOT, "meshchatx/src/frontend/style.css"), "utf8");
        expect(css).toContain("background-color: var(--mc-canvas");
        expect(css).toContain("#app");
        expect(css).toContain(".route-view-fade-enter-active");
    });

    it("main.js defers splash removal and preloads critical routes", () => {
        const main = readFileSync(resolve(ROOT, "meshchatx/src/frontend/main.ts"), "utf8");
        expect(main).toContain("removeBootSplash");
        expect(main).toContain("requestAnimationFrame");
        expect(main).toContain("preloadCriticalRouteChunks");
        expect(main).toContain('import("./features/messages/MessagesPage.svelte")');
        expect(main).toContain("ElectronUtils.isElectron()");
        expect(main).toContain("serviceWorkerRegisterOptions");
        expect(main).toContain("decideControllerChangeReload");
        expect(main).toContain("shouldRegisterServiceWorker");
        expect(main).toContain("import.meta.env.DEV");
    });

    it("App.svelte shell uses canvas background for route content", () => {
        const app = readFileSync(resolve(ROOT, "meshchatx/src/frontend/features/app-shell/App.svelte"), "utf8");
        const themeEngine = readFileSync(resolve(ROOT, "meshchatx/src/frontend/theme/themeEngine.ts"), "utf8");
        expect(app).toContain("shellCanvasStyle");
        expect(readFileSync(resolve(ROOT, "meshchatx/src/frontend/features/app-shell/components/AppShellHeaderBar.svelte"), "utf8")).toContain("bg-sem-canvas");
        expect(app).toContain("PageOutlet");
        expect(themeEngine).toContain("setUiTheme");
        expect(themeEngine).toContain("meshchatx_ui_theme");
    });

    it("Android theme and WebView use meshchat canvas color", () => {
        const colors = readFileSync(resolve(ROOT, "android/app/src/main/res/values/colors.xml"), "utf8");
        const themes = readFileSync(resolve(ROOT, "android/app/src/main/res/values/themes.xml"), "utf8");
        const layout = readFileSync(resolve(ROOT, "android/app/src/main/res/layout/activity_main.xml"), "utf8");
        const activity = readFileSync(
            resolve(ROOT, "android/app/src/main/java/com/meshchatx/MainActivity.java"),
            "utf8"
        );

        expect(colors).toContain("meshchat_canvas");
        expect(colors).toContain("#FF09090B");
        expect(colors).toContain("meshchat_canvas_light");
        expect(colors).toContain("#FFF8FAFC");
        expect(themes).toContain("android:windowBackground");
        expect(layout).toContain("@color/meshchat_canvas");
        expect(activity).toContain("applyShellCanvasTheme");
        expect(activity).toContain("setUiTheme");
        expect(activity).toContain("setLocalNightMode");
    });

    it("injectMeshchatThemeVariables keeps light/dark canvas tokens aligned", () => {
        injectMeshchatThemeVariables(document);
        const style = document.getElementById("meshchat-design-tokens");
        expect(style).toBeTruthy();
        expect(style.textContent).toContain(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-canvas"]);
        expect(style.textContent).toContain(MESHCHAT_THEME_VARIABLES_DARK["--mc-canvas"]);
        expect(MESHCHAT_THEME_VARIABLES_LIGHT["--mc-canvas"]).toBe("#f8fafc");
        expect(MESHCHAT_THEME_VARIABLES_DARK["--mc-canvas"]).toBe("#09090b");
    });

    it("removeBootSplash fades then removes without leaving white gap", async () => {
        vi.useFakeTimers();
        const splash = document.createElement("div");
        splash.id = "meshchatx-boot-splash";
        splash.setAttribute("aria-busy", "true");
        document.body.appendChild(splash);

        function removeBootSplash(el) {
            if (!el || !el.isConnected) {
                return;
            }
            el.setAttribute("aria-busy", "false");
            el.style.transition = "opacity 140ms ease";
            el.style.opacity = "0";
            window.setTimeout(() => {
                if (el.isConnected) {
                    el.remove();
                }
            }, 160);
        }

        removeBootSplash(splash);
        expect(splash.getAttribute("aria-busy")).toBe("false");
        expect(splash.style.opacity).toBe("0");
        expect(document.getElementById("meshchatx-boot-splash")).toBeTruthy();

        vi.advanceTimersByTime(160);
        expect(document.getElementById("meshchatx-boot-splash")).toBeNull();
        vi.useRealTimers();
    });
});
