// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import TranslatorPage from "@/features/translator/TranslatorPage.svelte";
import ToastUtils from "@/js/ToastUtils.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    canTranslate,
    computeSwappedLanguages,
    computeSyncedMode,
    filterLanguagesByMode,
    hasArgosLanguages,
} from "@/features/translator/lib/translatorEngine.ts";
import { registerTranslatorFeature } from "@/features/translator/index.ts";
import { clearRoutes, listRoutes } from "@/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "@/js/registries/featureRegistry.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

describe("translator lib helpers", () => {
    it("filters languages by translation mode", () => {
        const list = [
            { code: "en", name: "English", source: "argos" },
            { code: "de", name: "German", source: "libretranslate" },
        ];
        expect(filterLanguagesByMode(list, "argos")).toHaveLength(1);
        expect(filterLanguagesByMode(list, "argos")[0].code).toBe("en");
        expect(filterLanguagesByMode(list, "libretranslate")).toHaveLength(1);
        expect(filterLanguagesByMode(list, "libretranslate")[0].code).toBe("de");
    });

    it("checks for argos language packages", () => {
        expect(hasArgosLanguages([{ code: "en", name: "English", source: "argos" }])).toBe(true);
        expect(hasArgosLanguages([{ code: "de", name: "German", source: "libretranslate" }])).toBe(false);
    });

    it("evaluates canTranslate conditions", () => {
        const cfg = { translator_argos_enabled: true, translator_libretranslate_enabled: false };
        expect(
            canTranslate({
                config: cfg,
                mode: "argos",
                inputText: "hello",
                sourceLang: "en",
                targetLang: "de",
            })
        ).toBe(true);

        expect(
            canTranslate({
                config: cfg,
                mode: "argos",
                inputText: "",
                sourceLang: "en",
                targetLang: "de",
            })
        ).toBe(false);

        expect(
            canTranslate({
                config: cfg,
                mode: "argos",
                inputText: "hello",
                sourceLang: "en",
                targetLang: "en",
            })
        ).toBe(false);
    });

    it("computes synced mode according to installed backends", () => {
        expect(
            computeSyncedMode({
                currentMode: "argos",
                hasArgos: false,
                libreClientAvailable: true,
            })
        ).toBe("libretranslate");

        expect(
            computeSyncedMode({
                currentMode: "libretranslate",
                hasArgos: true,
                libreClientAvailable: false,
            })
        ).toBe("argos");
    });

    it("swaps languages and input text", () => {
        const res = computeSwappedLanguages({
            mode: "argos",
            currentSource: "en",
            currentTarget: "de",
            resultSource: "en",
            resultText: "Hallo Welt",
        });
        expect(res.newSource).toBe("de");
        expect(res.newTarget).toBe("en");
        expect(res.newInputText).toBe("Hallo Welt");
    });
});

describe("registerTranslatorFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers translator route correctly", () => {
        registerTranslatorFeature();
        expect(listFeatureIds()).toContain("translator");
        const route = listRoutes().find((r) => r.name === "translator");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/translator");
        expect(route?.mount).toBe("svelte");
    });
});

describe("TranslatorPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
        };
        window.api = axiosMock;

        registerTranslator(null);
        registerFallbackMessages({
            app: { tools: "Tools" },
            tools: {
                back_to_tools: "Back",
                translator: {
                    title: "Translator",
                    description: "Translate text between languages",
                },
            },
            common: {
                copied: "Copied",
            },
            translator: {
                source_language: "Source Language",
                target_language: "Target Language",
                auto_detect: "Auto Detect",
                select_target_language: "Select Target",
                text_to_translate: "Text to translate",
                enter_text_placeholder: "Enter text...",
                translate: "Translate",
                swap: "Swap",
                clear: "Clear",
                translation: "Translation",
                source: "Source",
                detected: "Detected",
                select_languages_warning: "Select languages",
                auto_detect_not_supported: "Auto detect not supported in Argos",
                failed_translate: "Failed to translate",
                failed_load_languages: "Failed to load languages",
                installed_languages: "Installed Languages",
                argos_translate: "Argos Translate",
                libretranslate: "LibreTranslate",
                api_server: "LibreTranslate API Server",
                api_server_description: "Base URL of LibreTranslate instance",
                api_key_optional: "API Key (Optional)",
                api_key_placeholder: "Leave empty if not required",
                api_key_description: "Only needed if required by server",
                backend_libretranslate: "LibreTranslate",
                backend_argos: "Argos Translate",
                backend_status: "Backend Status",
                libretranslate_url: "API URL",
                libretranslate_api_key: "API Key",
                privacy_mode_active: "Privacy Mode Active",
                privacy_mode_desc: "Outbound requests restricted",
            },
        });

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({
                    data: {
                        config: {
                            translator_argos_enabled: true,
                            translator_libretranslate_enabled: true,
                            libretranslate_url: "http://localhost:5000",
                            libretranslate_api_key: null,
                        },
                    },
                });
            }
            if (url === "/api/v1/translator/languages") {
                return Promise.resolve({
                    data: {
                        languages: [
                            { code: "en", name: "English", source: "argos" },
                            { code: "de", name: "German", source: "argos" },
                            { code: "en", name: "English", source: "libretranslate" },
                            { code: "de", name: "German", source: "libretranslate" },
                        ],
                        has_argos: true,
                        libre_client_available: true,
                        libretranslate_reachable: true,
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        axiosMock.post.mockResolvedValue({
            data: {
                translated_text: "Hallo Welt",
                source_lang: "en",
                target_lang: "de",
                source: "argos",
            },
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("renders the translator page and loads configuration", async () => {
        render(TranslatorPage);
        expect(screen.getByText("Translator")).toBeTruthy();

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
            expect(axiosMock.get).toHaveBeenCalledWith(
                "/api/v1/translator/languages",
                expect.any(Object)
            );
        });

        expect(await screen.findByText("Source Language")).toBeTruthy();
    });

    it("shows Libre tab when HTTP client is available even if server not reachable yet", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({
                    data: {
                        config: {
                            translator_argos_enabled: false,
                            translator_libretranslate_enabled: false,
                            libretranslate_url: "http://127.0.0.1:5000",
                            libretranslate_api_key: null,
                        },
                    },
                });
            }
            if (url === "/api/v1/translator/languages") {
                return Promise.resolve({
                    data: {
                        languages: [],
                        has_argos: false,
                        libre_client_available: true,
                        libretranslate_reachable: false,
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        render(TranslatorPage);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
        });

        expect(await screen.findByText("LibreTranslate API Server")).toBeTruthy();
    });

    it("switches translation modes", async () => {
        render(TranslatorPage);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
        });

        const libreBtn = await screen.findByRole("button", { name: "LibreTranslate" });
        await fireEvent.click(libreBtn);

        expect(screen.getByText("LibreTranslate API Server")).toBeTruthy();

        const argosBtn = screen.getByRole("button", { name: "Argos Translate" });
        await fireEvent.click(argosBtn);

        expect(screen.queryByText("LibreTranslate API Server")).toBeNull();
    });

    it("calls translate API and displays result", async () => {
        render(TranslatorPage);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
        });

        const sourceSelect = document.getElementById("translator-source-lang");
        const targetSelect = document.getElementById("translator-target-lang");
        const textarea = screen.getByPlaceholderText("Enter text...");

        if (sourceSelect) {
            await fireEvent.change(sourceSelect, { target: { value: "en" } });
        }
        if (targetSelect) {
            await fireEvent.change(targetSelect, { target: { value: "de" } });
        }
        await fireEvent.input(textarea, { target: { value: "Hello World" } });

        const translateBtn = screen.getByText("Translate");
        await fireEvent.click(translateBtn);

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith(
                "/api/v1/translator/translate",
                expect.objectContaining({
                    text: "Hello World",
                    source_lang: "en",
                    target_lang: "de",
                    use_argos: true,
                })
            );
        });

        expect(await screen.findByText("Hallo Welt")).toBeTruthy();
    });

    it("swaps languages when swap button is clicked", async () => {
        render(TranslatorPage);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
        });

        const sourceSelect = document.getElementById("translator-source-lang");
        const targetSelect = document.getElementById("translator-target-lang");

        if (sourceSelect) {
            await fireEvent.change(sourceSelect, { target: { value: "en" } });
        }
        if (targetSelect) {
            await fireEvent.change(targetSelect, { target: { value: "de" } });
        }

        const swapBtn = screen.getByText("Swap");
        await fireEvent.click(swapBtn);

        expect(sourceSelect?.value).toBe("de");
        expect(targetSelect?.value).toBe("en");
    });
});
