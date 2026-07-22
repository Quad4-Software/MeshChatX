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
                <option value="en">English</option>
                <option value="de">Deutsch</option>
                <option value="ru">Русский</option>
                <option value="it">Italiano</option>
            </select>
        </div>
    </section>
</template>

<script>
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
    methods: {
        onSelect(event) {
            this.$emit("change", event.target.value);
        },
    },
};
</script>
