// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import { createI18n } from "vue-i18n";
import { ensureLocaleMessages, listLocaleCodes, setLocale } from "../../meshchatx/src/frontend/js/localeLoader.js";

describe("localeLoader", () => {
    it("lists locale codes with english first", () => {
        const codes = listLocaleCodes();
        expect(codes[0]).toBe("en");
        expect(codes).toEqual(expect.arrayContaining(["de", "es", "fr", "ru", "zh"]));
        expect(new Set(codes).size).toBe(codes.length);
    });

    it("ensureLocaleMessages rejects bad codes without throwing", async () => {
        const i18n = createI18n({ legacy: false, locale: "en", messages: { en: { hi: "hi" } } });
        for (const bad of [null, undefined, "", 12, {}, [], "nope-xx"]) {
            await expect(ensureLocaleMessages(i18n, bad)).resolves.toBe(false);
        }
    });

    it("ensureLocaleMessages is idempotent for already-loaded locales", async () => {
        const i18n = createI18n({ legacy: false, locale: "en", messages: { en: { hi: "hi" } } });
        expect(await ensureLocaleMessages(i18n, "en")).toBe(true);
        expect(await ensureLocaleMessages(i18n, "en")).toBe(true);
    });

    it("loads a non-english locale into the composer", async () => {
        const i18n = createI18n({ legacy: false, locale: "en", messages: { en: { hi: "hi" } } });
        expect(i18n.global.availableLocales).not.toContain("de");
        expect(await ensureLocaleMessages(i18n, "de")).toBe(true);
        expect(i18n.global.availableLocales).toContain("de");
        expect(i18n.global.getLocaleMessage("de")._languageName).toBeTruthy();
    });

    it("setLocale updates locale.value for composition i18n", async () => {
        const i18n = createI18n({ legacy: false, locale: "en", messages: { en: { hi: "hi" } } });
        expect(await setLocale(i18n, "fr")).toBe(true);
        expect(i18n.global.locale.value).toBe("fr");
    });

    it("setLocale works when given the composer directly", async () => {
        const i18n = createI18n({ legacy: false, locale: "en", messages: { en: { hi: "hi" } } });
        expect(await setLocale(i18n.global, "es")).toBe(true);
        expect(i18n.global.locale.value).toBe("es");
    });

    it("ensureLocaleMessages returns false when setLocaleMessage is missing", async () => {
        const fake = { availableLocales: [], setLocaleMessage: undefined };
        expect(await ensureLocaleMessages(fake, "de")).toBe(false);
    });

    it("adversarial: ensureLocaleMessages(null) is false", async () => {
        expect(await ensureLocaleMessages(null, "en")).toBe(false);
        expect(await setLocale(undefined, "en")).toBe(false);
    });

    it("fuzz: random codes never throw", async () => {
        const i18n = createI18n({ legacy: false, locale: "en", messages: { en: {} } });
        const junk = ["", "en", "de", "../en", "EN", "en.json", "🚀", "a".repeat(200), "zh-CN", "pt"];
        for (const code of junk) {
            await expect(ensureLocaleMessages(i18n, code)).resolves.toBeTypeOf("boolean");
        }
    });
});
