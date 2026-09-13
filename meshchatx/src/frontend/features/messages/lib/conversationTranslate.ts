// SPDX-License-Identifier: 0BSD

import { STORAGE_KEYS } from "../../../js/constants.js";
import * as TranslationService from "../../../js/TranslationService.js";
import type { TranslationPack } from "../../../js/TranslationService.js";

export type LangOption = {
    value: string;
    label: string;
};

export type BubbleTranslation = {
    translatedText?: string;
    fromCode?: string;
    toCode?: string;
    showOriginal?: boolean;
    loading?: boolean;
};

function displayNames(): { of: (code: string) => string | undefined } {
    const locale = (typeof navigator !== "undefined" && navigator.language) || "en";
    try {
        return new Intl.DisplayNames([locale.slice(0, 2)], { type: "language" });
    } catch {
        return { of: (code: string) => code };
    }
}

function packToOption(pack: TranslationPack): LangOption {
    const names = displayNames();
    const from = pack.from || pack.pair.slice(0, 2);
    const to = pack.to || pack.pair.slice(2, 4);
    return {
        value: pack.pair,
        label: `${names.of(from) || from} → ${names.of(to) || to}`,
    };
}

/**
 * List installed offline translation packs as select options.
 * Option values are pair codes like "enes" understood by translateText.
 */
export async function loadTranslatorLanguages(): Promise<{ languages: LangOption[]; hasTranslator: boolean }> {
    try {
        const packs = await TranslationService.listPacks();
        const options = packs.map(packToOption).filter((opt) => Boolean(opt.value));
        return { languages: options, hasTranslator: options.length > 0 };
    } catch {
        return { languages: [], hasTranslator: false };
    }
}

/** Read the persisted translation target pair, if any. */
export function readSavedTranslateTarget(): string | null {
    let value: string | null = null;
    try {
        value =
            localStorage.getItem(STORAGE_KEYS.TRANSLATE_TARGET_LANG) ||
            localStorage.getItem(STORAGE_KEYS.COMPOSE_TRANSLATE_TARGET_LANG);
    } catch {
        value = null;
    }
    return value ? String(value).toLowerCase().slice(0, 8) : null;
}

/** Persist the chosen translation target pair for the next session. */
export function persistTranslateTarget(pair: string): void {
    const target = String(pair || "")
        .toLowerCase()
        .slice(0, 8);
    if (!target) {
        return;
    }
    try {
        localStorage.setItem(STORAGE_KEYS.TRANSLATE_TARGET_LANG, target);
        localStorage.setItem(STORAGE_KEYS.COMPOSE_TRANSLATE_TARGET_LANG, target);
    } catch {
        /* storage unavailable */
    }
}

/** Pick the persisted pair when still installed, else the first option. */
export function defaultTranslateTarget(options: LangOption[]): string {
    if (!options.length) {
        return "";
    }
    const saved = readSavedTranslateTarget();
    if (saved && options.some((opt) => opt.value === saved)) {
        return saved;
    }
    return options[0].value;
}

/**
 * Translate text through the local Bergamot engine. targetPair is a pack
 * pair code like "enes"; the first two letters are the source language.
 */
export async function translateText(params: {
    text: string;
    targetPair: string;
}): Promise<{ translatedText: string; sourceLang: string; targetLang: string }> {
    const pair = String(params.targetPair || "")
        .toLowerCase()
        .slice(0, 4);
    const source = pair.slice(0, 2);
    const target = pair.slice(2, 4);
    const result = await TranslationService.translate({
        from: source,
        to: target,
        text: params.text,
    });
    return {
        translatedText: String(result?.target?.text || ""),
        sourceLang: source,
        targetLang: target,
    };
}
