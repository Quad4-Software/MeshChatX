<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <nav class="settings-nav" :aria-label="$t('settings.nav_label')">
        <div class="settings-nav__mode" role="group" :aria-label="$t('settings.nav_mode_label')">
            <button
                type="button"
                class="settings-nav__mode-btn focus-ring-sem"
                :class="{ 'settings-nav__mode-btn--active': mode === 'simple' }"
                :aria-pressed="mode === 'simple' ? 'true' : 'false'"
                @click="$emit('update:mode', 'simple')"
            >
                {{ $t("settings.mode_simple") }}
            </button>
            <button
                type="button"
                class="settings-nav__mode-btn focus-ring-sem"
                :class="{ 'settings-nav__mode-btn--active': mode === 'advanced' }"
                :aria-pressed="mode === 'advanced' ? 'true' : 'false'"
                @click="$emit('update:mode', 'advanced')"
            >
                {{ $t("settings.mode_advanced") }}
            </button>
        </div>
        <button
            v-for="tab in visibleTabs"
            :key="tab.id"
            type="button"
            class="settings-nav__tab"
            :class="{
                'settings-nav__tab--active': tab.id === activeTab,
                'settings-nav__tab--empty': isSearchEmpty(tab.id),
            }"
            :aria-current="tab.id === activeTab ? 'page' : undefined"
            :disabled="isSearchEmpty(tab.id)"
            @click="onTabClick(tab.id)"
        >
            <span class="settings-nav__label-row">
                <span class="settings-nav__label">{{ $t(tab.labelKey) }}</span>
                <span v-if="searchActive" class="settings-nav__count">{{ matchCount(tab.id) }}</span>
            </span>
            <span class="settings-nav__description">{{ $t(tab.descriptionKey) }}</span>
        </button>
    </nav>
</template>

<script>
import { SETTINGS_TABS, isAdvancedSettingsSection } from "../../js/settings/settingsTabs.js";

export default {
    name: "SettingsNav",
    props: {
        activeTab: {
            type: String,
            required: true,
        },
        matchCounts: {
            type: Object,
            default: null,
        },
        mode: {
            type: String,
            default: "advanced",
        },
    },
    emits: ["select", "update:mode"],
    data() {
        return {
            tabs: SETTINGS_TABS,
        };
    },
    computed: {
        searchActive() {
            return this.matchCounts != null;
        },
        visibleTabs() {
            if (this.searchActive || this.mode !== "simple") {
                return this.tabs;
            }
            return this.tabs.filter((tab) => tab.sections.some((s) => !isAdvancedSettingsSection(s)));
        },
    },
    methods: {
        matchCount(tabId) {
            if (!this.matchCounts) return 0;
            const n = this.matchCounts[tabId];
            return typeof n === "number" && n > 0 ? n : 0;
        },
        isSearchEmpty(tabId) {
            return this.searchActive && this.matchCount(tabId) === 0;
        },
        onTabClick(tabId) {
            if (this.isSearchEmpty(tabId)) return;
            this.$emit("select", tabId);
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";

.settings-nav {
    @apply flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-x-visible lg:pb-0 lg:gap-0.5 lg:w-52 lg:shrink-0 lg:sticky lg:top-20 lg:self-start;
}

.settings-nav__mode {
    @apply flex gap-0.5 rounded-xl border border-sem-border bg-sem-surface-muted p-1 shrink-0 lg:mb-2 lg:w-full;
}

.settings-nav__mode-btn {
    @apply flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold text-sem-fg-muted transition-colors hover:text-sem-fg;
}

.settings-nav__mode-btn--active {
    @apply bg-sem-surface text-sem-fg shadow-xs;
}

.settings-nav__tab {
    @apply flex flex-col items-start gap-0.5 rounded-xl border border-transparent px-3 py-2.5 text-left transition-colors shrink-0 lg:w-full;
    @apply text-sem-fg-muted hover:bg-sem-surface-muted;
}

.settings-nav__tab--active {
    @apply border-sem-border bg-sem-surface text-sem-fg shadow-xs;
}

.settings-nav__tab--empty {
    @apply opacity-40 pointer-events-none;
}

.settings-nav__label-row {
    @apply flex items-center gap-2 w-full min-w-0;
}

.settings-nav__label {
    @apply text-sm font-semibold leading-tight min-w-0 truncate;
}

.settings-nav__count {
    @apply ml-auto text-[10px] font-semibold tabular-nums rounded-md px-1.5 py-0.5 bg-sem-surface-muted text-sem-fg-muted;
}

.settings-nav__description {
    @apply hidden text-xs text-sem-fg-muted lg:block;
}
</style>
