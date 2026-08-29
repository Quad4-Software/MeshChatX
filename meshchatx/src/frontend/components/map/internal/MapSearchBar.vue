<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="relative">
        <div class="flex items-center bg-sem-surface rounded-xl shadow-2xl border-0 ring-0">
            <input
                ref="inputEl"
                :value="modelValue"
                type="text"
                class="flex-1 px-4 py-2.5 bg-transparent text-sem-fg placeholder-gray-400 focus:outline-hidden focus:ring-0 border-0 text-sm"
                :placeholder="$t('map.search_placeholder')"
                @input="onInput"
                @keydown.enter="$emit('search')"
                @focus="$emit('focus')"
            />
            <button
                v-if="modelValue"
                class="p-2 text-sem-fg-muted hover:text-sem-fg transition-colors"
                @click="$emit('clear')"
            >
                <MaterialDesignIcon icon-name="close" class="size-[18px]" />
            </button>
            <button
                class="p-2 mr-1 text-blue-500 hover:text-blue-600 disabled:text-gray-300 transition-colors"
                :disabled="!modelValue || searching"
                @click="$emit('search')"
            >
                <MaterialDesignIcon
                    :icon-name="searching ? 'loading' : 'magnify'"
                    :class="['size-5', { 'animate-spin': searching }]"
                />
            </button>
        </div>

        <div
            v-if="showResults && (results.length > 0 || error)"
            class="absolute top-full left-0 right-0 mt-2 bg-sem-surface rounded-xl shadow-2xl border-0 overflow-y-auto z-40 max-h-64"
        >
            <div v-if="error" class="p-4 text-sm text-red-500 flex items-center gap-2">
                <MaterialDesignIcon icon-name="alert-circle" class="size-4" />
                {{ error }}
            </div>
            <button
                v-for="(result, index) in results"
                :key="index"
                class="w-full px-4 py-3 text-left hover:bg-sem-surface-muted/50 border-b border-gray-100/50 dark:border-zinc-800/50 last:border-b-0 transition-all"
                @click="$emit('select', result)"
            >
                <div class="font-bold text-sem-fg text-sm">{{ result.display_name }}</div>
                <div class="text-[10px] text-sem-fg-muted mt-0.5 font-bold uppercase tracking-wider">
                    {{ result.type }}
                </div>
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapSearchBar",
    components: { MaterialDesignIcon },
    props: {
        modelValue: { type: String, default: "" },
        results: { type: Array, default: () => [] },
        error: { type: String, default: null },
        searching: { type: Boolean, default: false },
        showResults: { type: Boolean, default: false },
    },
    emits: ["update:modelValue", "input", "search", "clear", "focus", "select"],
    methods: {
        onInput(event) {
            this.$emit("update:modelValue", event.target.value);
            this.$emit("input", event);
        },
    },
};
</script>
