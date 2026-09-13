// SPDX-License-Identifier: 0BSD

import { describe, expect, it, beforeAll } from "vitest";
import { get } from "svelte/store";
import { locale } from "svelte-i18n";
import {
    ensureLocaleMessages,
    getCurrentUiLocale,
    initSvelteI18n,
    listLocaleCodes,
    normalizeUiLocaleCode,
    setLocale,
} from "../../meshchatx/src/frontend/js/localeLoader.js";

describe("localeLoader", () => {
    beforeAll(async () => {
        await initSvelteI18n({ hi: "hi", _languageName: "English" });
    });

    it("lists locale codes with english first", () => {
        const codes = listLocaleCodes();
        expect(codes[0]).toBe("en");
        expect(codes).toEqual(expect.arrayContaining(["de", "es", "fr", "ru", "zh"]));
        expect(new Set(codes).size).toBe(codes.length);
    });

    it("ensureLocaleMessages rejects bad codes without throwing", async () => {
        for (const bad of [null, undefined, "", 12, {}, [], "nope-xx"]) {
            await expect(ensureLocaleMessages(null, bad)).resolves.toBe(false);
        }
    });

    it("ensureLocaleMessages is idempotent for already-loaded locales", async () => {
        expect(await ensureLocaleMessages(null, "en")).toBe(true);
        expect(await ensureLocaleMessages(null, "en")).toBe(true);
    });

    it("loads a non-english locale pack", async () => {
        expect(await ensureLocaleMessages(null, "de")).toBe(true);
        expect(await ensureLocaleMessages(null, "de")).toBe(true);
    });

    it("setLocale updates svelte-i18n locale store", async () => {
        expect(await setLocale(null, "fr")).toBe(true);
        expect(get(locale)).toBe("fr");
        expect(getCurrentUiLocale()).toBe("fr");
        expect(await setLocale(null, "en")).toBe(true);
        expect(get(locale)).toBe("en");
    });

    it("setLocale normalizes unknown packs to en", async () => {
        expect(await setLocale(null, "nope-xx")).toBe(true);
        expect(get(locale)).toBe("en");
        expect(await ensureLocaleMessages(null, "nope-xx")).toBe(false);
    });

    it("normalizeUiLocaleCode maps aliases and rejects unknown packs", () => {
        expect(normalizeUiLocaleCode("zh-cn")).toBe("zh");
        expect(normalizeUiLocaleCode("ru")).toBe("ru");
        expect(normalizeUiLocaleCode("jp")).toBe("en");
        expect(normalizeUiLocaleCode("")).toBe("en");
    });

    it("fuzz: random codes never throw", async () => {
        const junk = ["", "en", "de", "../en", "EN", "en.json", "a".repeat(200), "zh-CN", "pt"];
        for (const code of junk) {
            await expect(ensureLocaleMessages(null, code)).resolves.toBeTypeOf("boolean");
        }
    });
});
