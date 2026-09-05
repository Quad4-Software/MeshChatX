// SPDX-License-Identifier: 0BSD

import { mount, flushPromises } from "@vue/test-utils";
import { render } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import App from "../../meshchatx/src/frontend/components/App.vue";
import DocsPage from "../../meshchatx/src/frontend/features/docs/DocsPage.svelte";
import { resolveVisualiserIsDark } from "../../meshchatx/src/frontend/features/network-visualiser/lib/visualiserPrefs.js";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection";
import { normalizeUiLocaleCode } from "../../meshchatx/src/frontend/js/localeLoader.js";
import { createNetworkVisualiserWebGL } from "../../meshchatx/src/frontend/js/networkVisualiserWebGL.js";

const ROOT = resolve(import.meta.dirname, "../..");
const BOOT_THEME_JS = resolve(ROOT, "meshchatx/src/frontend/public/boot-theme.js");

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(() => false),
        on: vi.fn(),
        off: vi.fn(),
        connect: vi.fn(),
        destroy: vi.fn(),
    },
}));

function runBootThemeScript() {
    const code = readFileSync(BOOT_THEME_JS, "utf8");
    // eslint-disable-next-line no-new-func
    Function(code)();
}

function stubGlForClear() {
    return {
        createShader: () => ({}),
        shaderSource: vi.fn(),
        compileShader: vi.fn(),
        getShaderParameter: () => true,
        getShaderInfoLog: () => "",
        deleteShader: vi.fn(),
        createProgram: () => ({}),
        attachShader: vi.fn(),
        linkProgram: vi.fn(),
        getProgramParameter: () => true,
        getProgramInfoLog: () => "",
        deleteProgram: vi.fn(),
        createBuffer: () => ({}),
        bindBuffer: vi.fn(),
        bufferData: vi.fn(),
        createVertexArray: () => ({}),
        bindVertexArray: vi.fn(),
        enableVertexAttribArray: vi.fn(),
        vertexAttribPointer: vi.fn(),
        vertexAttribDivisor: vi.fn(),
        getUniformLocation: () => ({}),
        createTexture: () => ({}),
        bindTexture: vi.fn(),
        texParameteri: vi.fn(),
        texImage2D: vi.fn(),
        texSubImage2D: vi.fn(),
        generateMipmap: vi.fn(),
        pixelStorei: vi.fn(),
        deleteTexture: vi.fn(),
        deleteBuffer: vi.fn(),
        deleteVertexArray: vi.fn(),
        viewport: vi.fn(),
        clearColor: vi.fn(),
        clear: vi.fn(),
        enable: vi.fn(),
        blendFunc: vi.fn(),
        useProgram: vi.fn(),
        uniform2f: vi.fn(),
        uniform1f: vi.fn(),
        uniform1i: vi.fn(),
        activeTexture: vi.fn(),
        drawArrays: vi.fn(),
        drawArraysInstanced: vi.fn(),
        lineWidth: vi.fn(),
        TEXTURE_2D: 0x0de1,
        TEXTURE0: 0x84c0,
        RGBA: 0x1908,
        UNSIGNED_BYTE: 0x1401,
        LINEAR: 0x2601,
        LINEAR_MIPMAP_LINEAR: 0x2703,
        CLAMP_TO_EDGE: 0x812f,
        TEXTURE_MIN_FILTER: 0x2801,
        TEXTURE_MAG_FILTER: 0x2800,
        TEXTURE_WRAP_S: 0x2802,
        TEXTURE_WRAP_T: 0x2803,
        UNPACK_FLIP_Y_WEBGL: 0x9240,
        UNPACK_PREMULTIPLY_ALPHA_WEBGL: 0x9241,
        COLOR_BUFFER_BIT: 0x4000,
        BLEND: 0x0be2,
        SRC_ALPHA: 0x0302,
        ONE_MINUS_SRC_ALPHA: 0x0303,
        ARRAY_BUFFER: 0x8892,
        STATIC_DRAW: 0x88e4,
        DYNAMIC_DRAW: 0x88e8,
        FLOAT: 0x1406,
        TRIANGLES: 0x0004,
        LINES: 0x0001,
        VERTEX_SHADER: 0x8b31,
        FRAGMENT_SHADER: 0x8b30,
        COMPILE_STATUS: 0x8b81,
        LINK_STATUS: 0x8b82,
    };
}

describe("locale and theme regressions", () => {
    describe("App.vue config persistence", () => {
        let api;

        beforeEach(() => {
            api = {
                patch: vi.fn().mockImplementation(async (_url, body) => ({
                    data: { config: { language: "en", theme: "light", ...body } },
                })),
            };
            window.api = api;
            vi.clearAllMocks();
        });

        afterEach(() => {
            delete window.api;
        });

        it("updateConfig PATCHes language instead of relying on WebSocket-only config.set", async () => {
            const ctx = {
                config: { language: "en", theme: "light" },
                $t: (k) => k,
            };

            await App.methods.updateConfig.call(ctx, { language: "ru" }, "language");

            expect(api.patch).toHaveBeenCalledWith("/api/v1/config", { language: "ru" });
            expect(WebSocketConnection.send).not.toHaveBeenCalled();
            expect(ctx.config.language).toBe("ru");
        });

        it("onLanguageChange applies locale before PATCH so UI is not stuck on English", async () => {
            const order = [];
            const updateConfig = vi.fn().mockImplementation(async () => {
                order.push("updateConfig");
            });
            const applyLocale = vi.fn().mockImplementation(async () => {
                order.push("applyLocale");
            });
            const ctx = {
                updateConfig,
                applyLocale,
            };

            await App.methods.onLanguageChange.call(ctx, "zh-cn");

            expect(applyLocale).toHaveBeenCalledWith("zh");
            expect(updateConfig).toHaveBeenCalledWith({ language: "zh" }, "language");
            expect(order).toEqual(["applyLocale", "updateConfig"]);
        });
    });

    describe("DocsPage Reticulum manual language", () => {
        let axiosMock;
        let i18nMock;

        beforeEach(() => {
            axiosMock = {
                get: vi.fn().mockImplementation((url) => {
                    if (url.includes("/api/v1/docs/status")) {
                        return Promise.resolve({
                            data: {
                                status: "idle",
                                has_docs: true,
                                has_meshchatx_docs: false,
                            },
                        });
                    }
                    return Promise.resolve({ data: {} });
                }),
                patch: vi.fn().mockResolvedValue({ data: {} }),
            };
            window.api = axiosMock;
            i18nMock = { locale: "ru" };
        });

        afterEach(() => {
            delete window.api;
        });

        it("setLanguage does not overwrite app UI language in config", async () => {
            render(DocsPage);
            await flushPromises();

            expect(axiosMock.patch).not.toHaveBeenCalled();
            expect(i18nMock.locale).toBe("ru");
        });
    });

    describe("boot-theme.js", () => {
        beforeEach(() => {
            document.documentElement.className = "";
            delete document.documentElement.dataset.bootTheme;
            document.documentElement.style.colorScheme = "";
            window.localStorage.clear();
            delete window.MeshChatXAndroid;
        });

        afterEach(() => {
            document.documentElement.className = "";
            delete window.MeshChatXAndroid;
            window.localStorage.clear();
        });

        it("light boot removes stale html.dark class", () => {
            document.documentElement.classList.add("dark");
            window.localStorage.setItem("meshchatx_ui_theme", "light");
            runBootThemeScript();
            expect(document.documentElement.classList.contains("dark")).toBe(false);
            expect(document.documentElement.dataset.bootTheme).toBe("light");
        });
    });

    describe("network visualiser theme", () => {
        afterEach(() => {
            GlobalState.config = {};
            document.documentElement.classList.remove("dark");
        });

        it("resolveVisualiserIsDark follows GlobalState light theme over html.dark", () => {
            document.documentElement.classList.add("dark");
            GlobalState.config = { theme: "light" };
            expect(resolveVisualiserIsDark()).toBe(false);
        });

        it("resolveVisualiserIsDark follows GlobalState dark theme", () => {
            document.documentElement.classList.remove("dark");
            GlobalState.config = { theme: "dark" };
            expect(resolveVisualiserIsDark()).toBe(true);
        });

        it("clearBackground paints light framebuffer color", () => {
            const gl = stubGlForClear();
            const canvas = document.createElement("canvas");
            const host = document.createElement("div");
            host.appendChild(canvas);
            document.body.appendChild(host);
            Object.defineProperty(canvas, "clientWidth", { value: 320, configurable: true });
            Object.defineProperty(canvas, "clientHeight", { value: 240, configurable: true });
            canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 320, height: 240 });

            const renderer = createNetworkVisualiserWebGL(canvas, gl);
            renderer.clearBackground(false);
            expect(gl.clearColor).toHaveBeenCalledWith(0.973, 0.98, 0.988, 1);
            expect(gl.clear).toHaveBeenCalled();
            renderer.destroy();
            host.remove();
        });
    });

    describe("normalizeUiLocaleCode", () => {
        it("maps Reticulum manual codes away from invalid UI packs", () => {
            expect(normalizeUiLocaleCode("zh-cn")).toBe("zh");
            expect(normalizeUiLocaleCode("ru")).toBe("ru");
            expect(normalizeUiLocaleCode("jp")).toBe("en");
        });
    });
});
