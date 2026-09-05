// SPDX-License-Identifier: 0BSD

import type { TranslationMode, TranslatorConfig, TranslatorLanguage } from "./types.js";

/**
 * Filter language pairs matching active translation backend
 */
export function filterLanguagesByMode(
    languages: TranslatorLanguage[],
    mode: TranslationMode
): TranslatorLanguage[] {
    if (mode === "argos") {
        return languages.filter((lang) => lang.source === "argos");
    }
    return languages.filter((lang) => lang.source === "libretranslate");
}

/**
 * Check whether any Argos language packages are installed
 */
export function hasArgosLanguages(languages: TranslatorLanguage[]): boolean {
    return languages.some((lang) => lang.source === "argos");
}

/**
 * Check if translation can be initiated with current configuration
 */
export function canTranslate(params: {
    config: TranslatorConfig | null;
    mode: TranslationMode;
    inputText: string;
    sourceLang: string;
    targetLang: string;
}): boolean {
    const { config, mode, inputText, sourceLang, targetLang } = params;
    const argosEnabled = Boolean(config?.translator_argos_enabled);
    const libreEnabled = Boolean(config?.translator_libretranslate_enabled);
    const backendReady = (mode === "argos" && argosEnabled) || (mode === "libretranslate" && libreEnabled);

    return (
        backendReady &&
        inputText.trim().length > 0 &&
        Boolean(targetLang) &&
        targetLang !== sourceLang
    );
}

/**
 * Sync translation mode based on available installed backends
 */
export function computeSyncedMode(params: {
    currentMode: TranslationMode;
    hasArgos: boolean;
    libreClientAvailable: boolean;
}): TranslationMode {
    const { currentMode, hasArgos, libreClientAvailable } = params;

    if (currentMode === "argos" && !hasArgos && libreClientAvailable) {
        return "libretranslate";
    }
    if (currentMode === "libretranslate" && !libreClientAvailable && hasArgos) {
        return "argos";
    }
    if (hasArgos && !libreClientAvailable) {
        return "argos";
    }
    if (!hasArgos && libreClientAvailable) {
        return "libretranslate";
    }
    return currentMode;
}

/**
 * Calculate swapped source and target languages and optional updated text
 */
export function computeSwappedLanguages(params: {
    mode: TranslationMode;
    currentSource: string;
    currentTarget: string;
    resultSource?: string;
    resultText?: string;
}): {
    newSource: string;
    newTarget: string;
    newInputText?: string;
} {
    const { mode, currentSource, currentTarget, resultSource, resultText } = params;

    if (resultSource && resultSource !== "auto") {
        return {
            newSource: currentTarget,
            newTarget: currentSource,
            newInputText: resultText || undefined,
        };
    }

    if (mode === "argos") {
        return {
            newSource: currentTarget,
            newTarget: currentSource && currentSource !== "auto" ? currentSource : "",
        };
    }

    return {
        newSource: currentTarget || "auto",
        newTarget: currentSource && currentSource !== "auto" ? currentSource : "",
    };
}
