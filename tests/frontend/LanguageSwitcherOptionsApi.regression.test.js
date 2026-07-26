// SPDX-License-Identifier: 0BSD

/**
 * PROVED: setLocale(this.$i18n) under vue-i18n legacy:false loads packs and switches UI.
 * Bug class: incomplete-fix (Options API $i18n proxy lacks setLocaleMessage).
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import { nextTick } from "vue";
import {
    listLocaleCodes,
    normalizeUiLocaleCode,
    registerUiI18n,
    setLocale,
} from "../../meshchatx/src/frontend/js/localeLoader.js";
import LanguageSelector from "../../meshchatx/src/frontend/components/LanguageSelector.vue";
import en from "../../meshchatx/src/frontend/locales/en.json";
import de from "../../meshchatx/src/frontend/locales/de.json";

function createAppI18n() {
    return createI18n({
        legacy: false,
        locale: "en",
        fallbackLocale: "en",
        messages: { en },
    });
}

describe("language switcher Options API $i18n regression", () => {
    beforeEach(() => {
        registerUiI18n(null);
        document.documentElement.lang = "en";
    });

    afterEach(() => {
        registerUiI18n(null);
    });

    it("exposes a locale-only proxy on this.$i18n under legacy:false", () => {
        const i18n = createAppI18n();
        const wrapper = mount({ template: "<div />" }, { global: { plugins: [i18n] } });
        expect(typeof wrapper.vm.$i18n.setLocaleMessage).toBe("undefined");
        expect(typeof wrapper.vm.$i18n.locale).toBe("string");
    });

    it("fails closed without registerUiI18n when only the Options API proxy is passed", async () => {
        const i18n = createAppI18n();
        const wrapper = mount({ template: "<div />" }, { global: { plugins: [i18n] } });
        expect(await setLocale(wrapper.vm.$i18n, "de")).toBe(false);
        expect(i18n.global.locale.value).toBe("en");
    });

    it("setLocale(this.$i18n) switches after registerUiI18n", async () => {
        const i18n = createAppI18n();
        registerUiI18n(i18n);
        const Comp = {
            template: `<span id="label">{{ $t("app.language") }}</span>`,
            methods: {
                async switchTo(code) {
                    return setLocale(this.$i18n, code);
                },
            },
        };
        const wrapper = mount(Comp, { global: { plugins: [i18n] } });
        const before = wrapper.find("#label").text();
        expect(await wrapper.vm.switchTo("de")).toBe(true);
        await nextTick();
        expect(i18n.global.locale.value).toBe("de");
        expect(wrapper.vm.$i18n.locale).toBe("de");
        expect(document.documentElement.lang).toBe("de");
        expect(wrapper.find("#label").text()).toBe(de.app.language);
        expect(wrapper.find("#label").text()).not.toBe(before);
    });

    it("LanguageSelector selectLanguage applies locale via Options API proxy", async () => {
        const i18n = createAppI18n();
        registerUiI18n(i18n);
        const Parent = {
            components: { LanguageSelector },
            template: `
                <div>
                    <span id="msg">{{ $t("app.language") }}</span>
                    <LanguageSelector ref="lang" @language-change="onLanguageChange" />
                </div>
            `,
            data() {
                return { lastEmitted: null };
            },
            methods: {
                async onLanguageChange(langCode) {
                    this.lastEmitted = normalizeUiLocaleCode(langCode);
                    // Parent still persists config. Locale already applied by LanguageSelector.
                },
            },
        };
        const wrapper = mount(Parent, {
            global: {
                plugins: [i18n],
                stubs: { MaterialDesignIcon: true, Teleport: true },
            },
        });
        const selector = wrapper.findComponent({ name: "LanguageSelector" });
        expect(selector.exists()).toBe(true);
        await selector.vm.selectLanguage("de");
        await flushPromises();
        await nextTick();
        expect(i18n.global.locale.value).toBe("de");
        expect(wrapper.vm.lastEmitted).toBe("de");
        expect(wrapper.find("#msg").text()).toBe(de.app.language);
    });

    it("App-style handler recovers when only the Options API proxy is available", async () => {
        const i18n = createAppI18n();
        registerUiI18n(i18n);
        const Comp = {
            template: `<span id="msg">{{ $t("app.language") }}</span>`,
            methods: {
                async onLanguageChange(langCode) {
                    const code = normalizeUiLocaleCode(langCode);
                    await setLocale(this.$i18n, code);
                },
            },
        };
        const wrapper = mount(Comp, { global: { plugins: [i18n] } });
        await wrapper.vm.onLanguageChange("fr");
        await nextTick();
        expect(i18n.global.locale.value).toBe("fr");
        expect(wrapper.find("#msg").text()).not.toBe(en.app.language);
    });

    it("oracle: every bundled pack is reachable via Options API setLocale", async () => {
        const i18n = createAppI18n();
        registerUiI18n(i18n);
        const wrapper = mount({ template: "<div />" }, { global: { plugins: [i18n] } });
        const packs = listLocaleCodes();
        expect(packs.length).toBeGreaterThanOrEqual(8);
        for (const code of packs) {
            expect(await setLocale(wrapper.vm.$i18n, code)).toBe(true);
            expect(i18n.global.locale.value).toBe(code);
            expect(listAvailableLocalesOrThrow(i18n).includes(code)).toBe(true);
        }
    });
});

function listAvailableLocalesOrThrow(i18n) {
    const locales = i18n.global.availableLocales;
    if (!Array.isArray(locales)) {
        throw new Error("expected availableLocales array");
    }
    return locales;
}
