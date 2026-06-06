<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        v-if="open"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
        @click.self="$emit('close')"
    >
        <div
            class="flex w-full max-w-lg max-h-[min(36rem,90vh)] flex-col rounded-2xl border border-sem-border-card bg-sem-surface shadow-xl"
            role="dialog"
            :aria-label="$t('relay_chat.hub_icon_picker_title')"
        >
            <div class="flex items-center justify-between gap-2 border-b border-sem-border px-5 py-4">
                <h2 class="text-lg font-semibold">{{ $t("relay_chat.hub_icon_picker_title") }}</h2>
                <button
                    type="button"
                    class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60"
                    :title="$t('common.close')"
                    @click="$emit('close')"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>
            <div class="px-5 pt-3">
                <div class="relative">
                    <input
                        ref="searchInput"
                        v-model="search"
                        type="text"
                        :placeholder="$t('relay_chat.hub_icon_search', { count: iconNames.length })"
                        class="input-field !py-2.5 pr-10"
                    />
                    <MaterialDesignIcon
                        icon-name="magnify"
                        class="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-sem-fg-muted"
                    />
                </div>
            </div>
            <div class="flex-1 overflow-y-auto custom-scrollbar px-5 py-3">
                <div class="grid grid-cols-4 sm:grid-cols-5 gap-2">
                    <button
                        v-for="iconName in searchedIconNames"
                        :key="iconName"
                        type="button"
                        class="flex flex-col items-center gap-1 rounded-lg border p-2 transition-colors hover:bg-sem-surface/60"
                        :class="selectedIcon === iconName ? 'border-sem-accent bg-sem-accent/10' : 'border-sem-border'"
                        :title="iconName"
                        @click="pick(iconName)"
                    >
                        <MaterialDesignIcon :icon-name="iconName" class="size-7" :class="previewIconClass" />
                        <span class="w-full truncate text-center text-[10px] text-sem-fg-muted">{{ iconName }}</span>
                    </button>
                </div>
                <div v-if="searchedIconNames.length === 0" class="py-8 text-center text-sm text-sem-fg-muted">
                    {{ $t("relay_chat.hub_icon_no_results") }}
                </div>
                <div
                    v-else-if="searchedIconNames.length >= maxSearchResults"
                    class="pt-2 text-center text-xs text-sem-fg-muted"
                >
                    {{ $t("relay_chat.hub_icon_search_limit", { count: maxSearchResults }) }}
                </div>
            </div>
            <div class="flex justify-between gap-2 border-t border-sem-border px-5 py-3">
                <button type="button" :class="btnSecondary" @click="pick(null)">
                    {{ $t("relay_chat.hub_icon_reset_default") }}
                </button>
                <button type="button" :class="btnSecondary" @click="$emit('close')">
                    {{ $t("common.cancel") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import { nextTick } from "vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import { buildMdiIconNames } from "../js/mdiIconNames.js";

const BTN_SECONDARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg border border-sem-border bg-sem-surface-muted px-3 py-2 text-sm font-medium text-sem-fg transition hover:bg-sem-surface-raised";

export default {
    name: "MdiIconPickerModal",
    components: { MaterialDesignIcon },
    props: {
        open: {
            type: Boolean,
            default: false,
        },
        selectedIcon: {
            type: String,
            default: null,
        },
        previewIconClass: {
            type: String,
            default: "text-sem-fg-secondary",
        },
    },
    emits: ["close", "select"],
    data() {
        return {
            search: "",
            maxSearchResults: 200,
            iconNames: [],
            btnSecondary: BTN_SECONDARY,
        };
    },
    computed: {
        searchedIconNames() {
            const q = this.search.trim().toLowerCase();
            const list = q ? this.iconNames.filter((name) => name.includes(q)) : this.iconNames;
            return list.slice(0, this.maxSearchResults);
        },
    },
    watch: {
        open(isOpen) {
            if (isOpen) {
                this.search = "";
                nextTick(() => {
                    const el = this.$refs.searchInput;
                    if (el && typeof el.focus === "function") {
                        el.focus();
                    }
                });
            }
        },
    },
    mounted() {
        this.iconNames = buildMdiIconNames();
    },
    methods: {
        pick(iconName) {
            this.$emit("select", iconName);
            this.$emit("close");
        },
    },
};
</script>
