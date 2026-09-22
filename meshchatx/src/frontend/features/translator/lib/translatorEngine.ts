// SPDX-License-Identifier: 0BSD

import type { InstalledPair, LanguageOption, TranslationPack } from "./types.js";

/**
 * Display names for ISO language codes in the user locale, with a safe
 * fallback for environments without Intl.DisplayNames.
 */
export function languageDisplayNames(locale?: string): { of: (code: string) => string | undefined } {
    const userLocale = String(locale || "en").slice(0, 2);
    try {
        return new Intl.DisplayNames([userLocale], { type: "language" });
    } catch {
        return { of: (code: string) => code };
    }
}

/** Normalize a pack record into a from/to pair. */
export function installedPairs(packs: TranslationPack[]): InstalledPair[] {
    return packs.map((pack) => ({
        pair: pack.pair,
        from: pack.from || pack.pair.slice(0, 2),
        to: pack.to || pack.pair.slice(2, 4),
    }));
}

/** Sorted unique language options across all installed packs. */
export function languageOptions(packs: TranslationPack[], locale?: string): LanguageOption[] {
    const displayNames = languageDisplayNames(locale);
    const codes = new Set<string>();
    for (const pair of installedPairs(packs)) {
        codes.add(pair.from);
        codes.add(pair.to);
    }
    const options = Array.from(codes).map((code) => ({
        value: code,
        label: displayNames.of(code) || code,
    }));
    return options.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));
}

/**
 * Pick a sensible default source/target from the installed packs.
 * Prefers a pair whose endpoints differ.
 */
export function guessDefaultLanguages(packs: TranslationPack[]): { source: string; target: string } {
    if (!packs.length) {
        return { source: "", target: "" };
    }
    const first = packs[0];
    let source = first.from || first.pair.slice(0, 2);
    let target = first.to || first.pair.slice(2, 4);
    if (source === target) {
        const diff = packs.find((pack) => (pack.from || pack.pair.slice(0, 2)) !== (pack.to || pack.pair.slice(2, 4)));
        if (diff) {
            source = diff.from || diff.pair.slice(0, 2);
            target = diff.to || diff.pair.slice(2, 4);
        }
    }
    return { source, target };
}

/** Human readable "English → Spanish" style label for a pack. */
export function packLabel(pack: TranslationPack, locale?: string): string {
    const displayNames = languageDisplayNames(locale);
    const from = pack.from || pack.pair.slice(0, 2);
    const to = pack.to || pack.pair.slice(2, 4);
    return `${displayNames.of(from) || from} → ${displayNames.of(to) || to}`;
}

/** Whether a translation can run with the current selection. */
export function canTranslate(inputText: string, sourceLang: string, targetLang: string): boolean {
    return Boolean(inputText.trim()) && Boolean(sourceLang) && Boolean(targetLang) && sourceLang !== targetLang;
}
