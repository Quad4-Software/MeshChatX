// SPDX-License-Identifier: 0BSD

import { describe, expect, it, afterEach } from "vitest";
import { createI18n } from "vue-i18n";
import {
    canonicalizeBcp47Locale,
    ensureLocaleMessages,
    listLocaleCodes,
    listLocaleOptions,
    normalizeUiLocaleCode,
    registerUiI18n,
    setLocale,
} from "../../meshchatx/src/frontend/js/localeLoader.js";

describe("localeLoader", () => {
    afterEach(() => {
        registerUiI18n(null);
    });

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

    it("normalizeUiLocaleCode maps aliases and rejects unknown packs", () => {
        expect(normalizeUiLocaleCode("zh-cn")).toBe("zh");
        expect(normalizeUiLocaleCode("ru")).toBe("ru");
        expect(normalizeUiLocaleCode("jp")).toBe("en");
        expect(normalizeUiLocaleCode("")).toBe("en");
    });

    it("fuzz: random codes never throw", async () => {
        const i18n = createI18n({ legacy: false, locale: "en", messages: { en: {} } });
        const junk = ["", "en", "de", "../en", "EN", "en.json", "🚀", "a".repeat(200), "zh-CN", "pt"];
        for (const code of junk) {
            await expect(ensureLocaleMessages(i18n, code)).resolves.toBeTypeOf("boolean");
        }
    });

    it("registerUiI18n lets setLocale recover from a locale-only proxy", async () => {
        const i18n = createI18n({ legacy: false, locale: "en", messages: { en: { hi: "hi" } } });
        const proxy = {
            locale: "en",
            availableLocales: ["en"],
            fallbackLocale: "en",
        };
        expect(await setLocale(proxy, "de")).toBe(false);
        registerUiI18n(i18n);
        expect(await setLocale(proxy, "de")).toBe(true);
        expect(i18n.global.locale.value).toBe("de");
    });

    describe("BCP 47 locale tags", () => {
        it("canonicalizeBcp47Locale normalizes case and underscores", () => {
            expect(canonicalizeBcp47Locale("pt-br")).toBe("pt-BR");
            expect(canonicalizeBcp47Locale("pt_br")).toBe("pt-BR");
            expect(canonicalizeBcp47Locale("PT-BR")).toBe("pt-BR");
            expect(canonicalizeBcp47Locale("zh-cn")).toBe("zh-CN");
            expect(canonicalizeBcp47Locale("ZH_HANS")).toBe("zh-Hans");
        });

        it("listLocaleCodes exposes BCP 47 canonical tags", () => {
            const codes = listLocaleCodes();
            expect(codes).toContain("pt-BR");
            expect(codes).not.toContain("pt-br");
            expect(codes).toEqual(expect.arrayContaining(["en", "de", "fr", "ru", "zh"]));
        });

        it("listLocaleOptions returns native names and BCP 47 codes", () => {
            const options = listLocaleOptions();
            const pt = options.find((o) => o.code === "pt-BR");
            expect(pt).toBeDefined();
            expect(pt?.name).toBe("Português (Brasil)");
            expect(options.some((o) => o.code === "zh" && o.name === "中文")).toBe(true);
        });

        it("normalizeUiLocaleCode maps legacy and mixed-case tags to BCP 47 packs", () => {
            expect(normalizeUiLocaleCode("pt-br")).toBe("pt-BR");
            expect(normalizeUiLocaleCode("pt_br")).toBe("pt-BR");
            expect(normalizeUiLocaleCode("PT-BR")).toBe("pt-BR");
            expect(normalizeUiLocaleCode("pt")).toBe("en");
            expect(normalizeUiLocaleCode("zh-cn")).toBe("zh");
            expect(normalizeUiLocaleCode("zh-Hans")).toBe("zh");
        });

        it("setLocale loads and applies a BCP 47 region tag", async () => {
            const i18n = createI18n({ legacy: false, locale: "en", messages: { en: { hi: "hi" } } });
            expect(await setLocale(i18n, "pt-BR")).toBe(true);
            expect(i18n.global.locale.value).toBe("pt-BR");
            expect(i18n.global.getLocaleMessage("pt-BR")._languageName).toBe("Português (Brasil)");
        });
    });
});
