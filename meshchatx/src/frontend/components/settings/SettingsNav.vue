<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <nav class="settings-nav" aria-label="Settings sections">
        <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="settings-nav__tab"
            :class="{ 'settings-nav__tab--active': tab.id === activeTab }"
            :aria-current="tab.id === activeTab ? 'page' : undefined"
            @click="$emit('select', tab.id)"
        >
            <span class="settings-nav__label">{{ $t(tab.labelKey) }}</span>
            <span class="settings-nav__description">{{ $t(tab.descriptionKey) }}</span>
        </button>
    </nav>
</template>

<script>
import { SETTINGS_TABS } from "../../js/settings/settingsTabs.js";

export default {
    name: "SettingsNav",
    props: {
        activeTab: {
            type: String,
            required: true,
        },
    },
    emits: ["select"],
    data() {
        return {
            tabs: SETTINGS_TABS,
        };
    },
};
</script>

<style scoped>
@reference "../../style.css";

.settings-nav {
    @apply flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-x-visible lg:pb-0 lg:gap-0.5 lg:w-52 lg:shrink-0 lg:sticky lg:top-20 lg:self-start;
}

.settings-nav__tab {
    @apply flex flex-col items-start gap-0.5 rounded-xl border border-transparent px-3 py-2.5 text-left transition-colors shrink-0 lg:w-full;
    @apply text-gray-600 dark:text-zinc-400 hover:bg-white/70 dark:hover:bg-zinc-900/70;
}

.settings-nav__tab--active {
    @apply border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-gray-900 dark:text-white shadow-xs;
}

.settings-nav__label {
    @apply text-sm font-semibold leading-tight;
}

.settings-nav__description {
    @apply hidden text-xs text-gray-500 dark:text-zinc-500 lg:block;
}
</style>
