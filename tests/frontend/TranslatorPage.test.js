// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import TranslatorPage from "@/features/translator/TranslatorPage.svelte";
import ToastUtils from "@/js/ToastUtils.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import * as TranslationService from "@/js/TranslationService.js";
import {
    canTranslate,
    guessDefaultLanguages,
    installedPairs,
    languageOptions,
    packLabel,
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

vi.mock("@/js/TranslationService.js", () => ({
    listPacks: vi.fn(),
    importPack: vi.fn(),
    removePack: vi.fn(),
    refreshPacks: vi.fn(),
    translate: vi.fn(),
}));

const PACKS = [
    { pair: "enes", from: "en", to: "es", size: 1024 * 2048 },
    { pair: "deen", from: "de", to: "en", size: 1024 * 1024 },
];

describe("translator lib helpers", () => {
    it("normalizes packs into from/to pairs", () => {
        expect(installedPairs(PACKS)).toEqual([
            { pair: "enes", from: "en", to: "es" },
            { pair: "deen", from: "de", to: "en" },
        ]);
        expect(installedPairs([{ pair: "fren" }])).toEqual([{ pair: "fren", from: "fr", to: "en" }]);
    });

    it("builds sorted unique language options from packs", () => {
        const options = languageOptions(PACKS, "en");
        const values = options.map((o) => o.value);
        expect(new Set(values)).toEqual(new Set(["en", "es", "de"]));
        expect(values).toHaveLength(3);
        expect(options.every((o) => typeof o.label === "string" && o.label.length > 0)).toBe(true);
    });

    it("guesses default languages from the first usable pack", () => {
        expect(guessDefaultLanguages(PACKS)).toEqual({ source: "en", target: "es" });
        expect(guessDefaultLanguages([])).toEqual({ source: "", target: "" });
    });

    it("renders a readable pack label", () => {
        const label = packLabel({ pair: "enes", from: "en", to: "es", size: 1 }, "en");
        expect(label).toContain("English");
        expect(label).toContain("Spanish");
    });

    it("evaluates canTranslate conditions", () => {
        expect(canTranslate("hello", "en", "es")).toBe(true);
        expect(canTranslate("", "en", "es")).toBe(false);
        expect(canTranslate("hello", "en", "en")).toBe(false);
        expect(canTranslate("hello", "", "es")).toBe(false);
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
    beforeEach(() => {
        vi.clearAllMocks();

        TranslationService.listPacks.mockResolvedValue(PACKS);
        TranslationService.importPack.mockResolvedValue({ pairs: ["enes"] });
        TranslationService.removePack.mockResolvedValue({ removed: "enes" });
        TranslationService.translate.mockResolvedValue({ target: { text: "Hola mundo" } });

        registerTranslator(null);
        registerFallbackMessages({
            tools: {
                translator: {
                    title: "Translator",
                    description: "Translate text offline with locally imported language packs.",
                },
            },
            translator: {
                pack_library: "Pack Library",
                pack_library_description: "Import and manage local translation packs.",
                import_pack: "Import pack",
                importing: "Importing...",
                remove: "Remove",
                no_packs: "No packs installed. Import a pack archive to translate offline.",
                pair_code: "Pair {pair}",
                size_kb: "{size} KB",
                source_language: "Source language",
                target_language: "Target language",
                swap_languages: "Swap languages",
                input_text: "Text to translate",
                input_placeholder: "Enter text to translate...",
                output_text: "Translation",
                translate: "Translate",
                translating: "Translating...",
                clear: "Clear",
                copy: "Copy",
                translation_failed: "Translation failed.",
                load_packs_failed: "Failed to load installed packs.",
            },
            common: {
                copied: "Copied",
            },
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders the pack library and lists installed packs", async () => {
        render(TranslatorPage);
        expect(screen.getByText("Translator")).toBeTruthy();
        expect(screen.getByText("Pack Library")).toBeTruthy();

        await waitFor(() => {
            expect(TranslationService.listPacks).toHaveBeenCalledTimes(1);
        });

        expect((await screen.findAllByText(/Pair ENES/)).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Pair DEEN/).length).toBeGreaterThan(0);
    });

    it("shows the empty state when no packs are installed", async () => {
        TranslationService.listPacks.mockResolvedValue([]);
        render(TranslatorPage);

        expect(await screen.findByText("No packs installed. Import a pack archive to translate offline.")).toBeTruthy();
    });

    it("imports a pack through the hidden file input", async () => {
        const { container } = render(TranslatorPage);
        await waitFor(() => {
            expect(TranslationService.listPacks).toHaveBeenCalledTimes(1);
        });

        const fileInput = container.querySelector('input[type="file"]');
        expect(fileInput).toBeTruthy();
        const file = new File(["archive"], "enes.zip", { type: "application/zip" });
        Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
        await fireEvent.change(fileInput);

        await waitFor(() => {
            expect(TranslationService.importPack).toHaveBeenCalledWith(file);
        });
        await waitFor(() => {
            expect(TranslationService.listPacks).toHaveBeenCalledTimes(2);
        });
    });

    it("removes a pack via its remove button", async () => {
        render(TranslatorPage);
        await waitFor(() => {
            expect(TranslationService.listPacks).toHaveBeenCalledTimes(1);
        });

        const removeButtons = await screen.findAllByRole("button", { name: "Remove" });
        await fireEvent.click(removeButtons[0]);

        await waitFor(() => {
            expect(TranslationService.removePack).toHaveBeenCalledWith("enes");
        });
        await waitFor(() => {
            expect(TranslationService.listPacks).toHaveBeenCalledTimes(2);
        });
    });

    it("translates text with the selected pack languages", async () => {
        render(TranslatorPage);
        await waitFor(() => {
            expect(TranslationService.listPacks).toHaveBeenCalledTimes(1);
        });

        const sourceSelect = document.getElementById("translator-source-lang");
        const targetSelect = document.getElementById("translator-target-lang");
        const textarea = screen.getByPlaceholderText("Enter text to translate...");

        await fireEvent.change(sourceSelect, { target: { value: "en" } });
        await fireEvent.change(targetSelect, { target: { value: "es" } });
        await fireEvent.input(textarea, { target: { value: "Hello world" } });

        await fireEvent.click(screen.getByRole("button", { name: "Translate" }));

        await waitFor(() => {
            expect(TranslationService.translate).toHaveBeenCalledWith({
                from: "en",
                to: "es",
                text: "Hello world",
            });
        });

        expect(await screen.findByText("Hola mundo")).toBeTruthy();
    });

    it("swaps source and target languages", async () => {
        render(TranslatorPage);
        await waitFor(() => {
            expect(TranslationService.listPacks).toHaveBeenCalledTimes(1);
        });

        const sourceSelect = document.getElementById("translator-source-lang");
        const targetSelect = document.getElementById("translator-target-lang");

        await fireEvent.change(sourceSelect, { target: { value: "en" } });
        await fireEvent.change(targetSelect, { target: { value: "es" } });

        await fireEvent.click(screen.getByRole("button", { name: "Swap languages" }));

        expect(sourceSelect.value).toBe("es");
        expect(targetSelect.value).toBe("en");
    });

    it("surfaces a pack list failure as an error message", async () => {
        TranslationService.listPacks.mockRejectedValue(new Error("boom"));
        render(TranslatorPage);

        expect(await screen.findByText("Failed to load installed packs.")).toBeTruthy();
    });
});
