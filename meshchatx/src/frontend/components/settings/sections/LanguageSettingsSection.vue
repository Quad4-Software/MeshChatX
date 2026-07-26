<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">i18n</div>
                <h2>{{ $t("app.language") }}</h2>
                <p>{{ $t("app.select_language") }}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <select :value="language" class="input-field" @change="onSelect">
                <option v-for="lang in languages" :key="lang.code" :value="lang.code">
                    {{ lang.name }}
                </option>
            </select>
        </div>
    </section>
</template>

<script>
import { listLocaleCodes } from "../../../js/localeLoader.js";

const LANGUAGE_NAMES = {
    de: "Deutsch",
    en: "English",
    es: "Español",
    fi: "Suomi",
    fr: "Français",
    it: "Italiano",
    nl: "Nederlands",
    ru: "Русский",
    zh: "中文",
};

const discoveredLanguages = listLocaleCodes().map((code) => ({
    code,
    name: LANGUAGE_NAMES[code] || code,
}));

export default {
    name: "LanguageSettingsSection",
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        language: {
            type: String,
            default: "en",
        },
    },
    emits: ["change"],
    computed: {
        languages() {
            return discoveredLanguages;
        },
    },
    methods: {
        onSelect(event) {
            this.$emit("change", event.target.value);
        },
    },
};
</script>
