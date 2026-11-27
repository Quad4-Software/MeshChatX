<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="relative group">
        <MaterialDesignIcon
            :icon-name="icon"
            class="absolute left-3 top-1/2 -translate-y-1/2 shrink-0 text-sem-fg-muted group-focus-within:text-sem-accent transition-colors pointer-events-none z-10"
            :class="compact ? 'size-4' : 'size-5'"
        />
        <input
            ref="inputRef"
            :value="modelValue"
            type="text"
            :placeholder="placeholder"
            :class="compact ? 'search-input search-input-compact' : 'search-input'"
            v-bind="$attrs"
            @input="onInput"
            @keydown.esc="clear"
        />
        <div v-if="loading" class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
            <MaterialDesignIcon
                icon-name="loading"
                :class="[compact ? 'size-3.5' : 'size-4', 'text-sem-fg-muted animate-spin']"
            />
        </div>
        <button
            v-else-if="modelValue"
            type="button"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center text-sem-fg-muted hover:text-sem-fg focus-ring-sem rounded-full p-0.5 transition-colors"
            :title="clearTitle || $t('common.clear')"
            @click="clear"
        >
            <MaterialDesignIcon icon-name="close-circle" :class="compact ? 'size-4' : 'size-5'" />
        </button>
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

defineOptions({ inheritAttrs: false });

withDefaults(
    defineProps<{
        modelValue?: string;
        placeholder?: string;
        icon?: string;
        compact?: boolean;
        clearTitle?: string;
        loading?: boolean;
    }>(),
    {
        modelValue: "",
        placeholder: "",
        icon: "magnify",
        compact: false,
        clearTitle: "",
        loading: false,
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: string];
    clear: [];
}>();

function onInput(event: Event) {
    emit("update:modelValue", (event.target as HTMLInputElement).value);
}

function clear() {
    emit("update:modelValue", "");
    emit("clear");
}

const inputRef = ref<HTMLInputElement | null>(null);

function focus() {
    inputRef.value?.focus();
}

defineExpose({ focus });
</script>
