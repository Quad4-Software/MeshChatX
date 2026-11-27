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
            <select :value="selectedLanguage" class="input-field" @change="onSelect">
                <option v-for="lang in languages" :key="lang.code" :value="lang.code">
                    {{ lang.name }}
                </option>
            </select>
        </div>
    </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { listLocaleOptions, normalizeUiLocaleCode } from "../../../js/localeLoader.js";

const props = withDefaults(
    defineProps<{
        visible?: boolean;
        language?: string;
    }>(),
    {
        visible: true,
        language: "en",
    }
);

const emit = defineEmits<{
    change: [language: string];
}>();

const languages = listLocaleOptions();
const selectedLanguage = computed(() => normalizeUiLocaleCode(props.language));

function onSelect(event: Event) {
    emit("change", (event.target as HTMLSelectElement).value);
}
</script>
