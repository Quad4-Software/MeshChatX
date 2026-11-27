<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="space-y-4">
        <div class="flex items-center gap-4">
            <div class="p-4 bg-sem-surface-muted rounded-xl shrink-0">
                <LxmfUserIcon
                    :key="draftKey"
                    :icon-name="draft.icon_name"
                    :icon-foreground-colour="draft.fg_color"
                    :icon-background-colour="draft.bg_color"
                    icon-class="size-14"
                />
            </div>
            <div class="flex-1 space-y-3 min-w-0">
                <div class="flex items-center justify-between gap-3">
                    <label class="text-sm font-medium text-sem-fg-muted">{{ $t("bots.icon_background") }}</label>
                    <div class="flex items-center gap-2">
                        <ColourPickerDropdown :colour="draft.bg_color" @update:colour="setBg" />
                        <input
                            :value="draft.bg_color"
                            type="text"
                            class="w-24 px-2 py-1.5 text-xs border border-sem-border rounded-lg bg-sem-surface text-sem-fg font-mono"
                            placeholder="#e5e7eb"
                            @input="setBg($event.target.value)"
                        />
                    </div>
                </div>
                <div class="flex items-center justify-between gap-3">
                    <label class="text-sm font-medium text-sem-fg-muted">{{ $t("bots.icon_foreground") }}</label>
                    <div class="flex items-center gap-2">
                        <ColourPickerDropdown :colour="draft.fg_color" @update:colour="setFg" />
                        <input
                            :value="draft.fg_color"
                            type="text"
                            class="w-24 px-2 py-1.5 text-xs border border-sem-border rounded-lg bg-sem-surface text-sem-fg font-mono"
                            placeholder="#6b7280"
                            @input="setFg($event.target.value)"
                        />
                    </div>
                </div>
            </div>
        </div>

        <SearchInput v-model="search" :placeholder="$t('bots.icon_search', { count: iconNames.length })" />
        <div
            class="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-56 overflow-y-auto p-1 rounded-lg border border-sem-border"
        >
            <button
                v-for="name of searchedIconNames"
                :key="name"
                type="button"
                class="flex flex-col items-center justify-center p-2.5 rounded-lg border-2 transition-all hover:bg-sem-surface-muted hover:border-sem-accent dark:hover:border-sem-accent"
                :class="draft.icon_name === name ? 'border-sem-accent bg-sem-surface-muted' : 'border-sem-border'"
                :title="name"
                @click="selectIcon(name)"
            >
                <LxmfUserIcon
                    :icon-name="name"
                    :icon-foreground-colour="draft.icon_name === name ? draft.fg_color : '#6b7280'"
                    :icon-background-colour="draft.icon_name === name ? draft.bg_color : '#e5e7eb'"
                    icon-class="size-8"
                />
                <div class="mt-1.5 text-[10px] text-center text-sem-fg-muted truncate w-full">
                    {{ name }}
                </div>
            </button>
        </div>
        <div v-if="searchedIconNames.length === 0" class="text-center py-4 text-sm text-sem-fg-muted">
            {{ $t("bots.icon_search_empty") }}
        </div>

        <div class="flex items-center justify-between gap-2">
            <span class="text-xs text-sem-fg-muted">{{ $t("bots.icon_hint") }}</span>
            <button v-if="modelValue" type="button" class="text-xs text-sem-danger hover:underline" @click="clear">
                {{ $t("bots.icon_remove") }}
            </button>
        </div>
    </div>
</template>

<script lang="ts">
export { defaultBotIconDraft } from "./lxmfIconDraft";
</script>

<script setup lang="ts">
import * as mdi from "@mdi/js";
import { computed, onMounted, ref } from "vue";
import ColourPickerDropdown from "./ColourPickerDropdown.vue";
import LxmfUserIcon from "./LxmfUserIcon.vue";
import SearchInput from "./SearchInput.vue";
import { type BotIconDraft } from "./lxmfIconDraft";

const DEFAULT_FG = "#6b7280";
const DEFAULT_BG = "#e5e7eb";

const props = withDefaults(
    defineProps<{
        modelValue?: BotIconDraft | null;
    }>(),
    {
        modelValue: null,
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: BotIconDraft | null];
}>();

const search = ref("");
const maxSearchResults = 200;
const iconNames = ref<string[]>([]);

const draft = computed<BotIconDraft>(() => {
    const v = props.modelValue;
    return {
        icon_name: v && v.icon_name ? v.icon_name : "",
        fg_color: v && v.fg_color ? v.fg_color : DEFAULT_FG,
        bg_color: v && v.bg_color ? v.bg_color : DEFAULT_BG,
    };
});

const draftKey = computed(() => `${draft.value.icon_name}|${draft.value.fg_color}|${draft.value.bg_color}`);

const searchedIconNames = computed(() => {
    const q = search.value.toLowerCase();
    return iconNames.value.filter((name) => name.toLowerCase().includes(q)).slice(0, maxSearchResults);
});

onMounted(() => {
    iconNames.value = Object.keys(mdi).map((name) =>
        name
            .replace(/^mdi/, "")
            .replace(/([a-z])([A-Z])/g, "$1-$2")
            .toLowerCase()
    );
});

function patchDraft(patch: Partial<BotIconDraft>) {
    const next = { ...draft.value, ...patch };
    if (!next.icon_name) {
        emit("update:modelValue", null);
        return;
    }
    emit("update:modelValue", next);
}

function selectIcon(name: string) {
    patchDraft({ icon_name: name });
}

function setFg(value: string) {
    patchDraft({ fg_color: String(value || "").trim() });
}

function setBg(value: string) {
    patchDraft({ bg_color: String(value || "").trim() });
}

function clear() {
    emit("update:modelValue", null);
}
</script>
