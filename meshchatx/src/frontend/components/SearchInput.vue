<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="relative group">
        <MaterialDesignIcon
            :icon-name="icon"
            class="absolute left-3 top-1/2 -translate-y-1/2 shrink-0 text-gray-400 group-focus-within:text-sem-accent transition-colors pointer-events-none z-10"
            :class="compact ? 'size-4' : 'size-5'"
        />
        <input
            :value="modelValue"
            type="text"
            :placeholder="placeholder"
            :class="compact ? 'search-input search-input-compact' : 'search-input'"
            v-bind="$attrs"
            @input="$emit('update:modelValue', $event.target.value)"
            @keydown.esc="clear"
        />
        <div v-if="loading" class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
            <MaterialDesignIcon
                icon-name="loading"
                :class="[compact ? 'size-3.5' : 'size-4', 'text-gray-400 animate-spin']"
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

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

export default {
    name: "SearchInput",
    components: {
        MaterialDesignIcon,
    },
    inheritAttrs: false,
    props: {
        modelValue: {
            type: String,
            default: "",
        },
        placeholder: {
            type: String,
            default: "",
        },
        icon: {
            type: String,
            default: "magnify",
        },
        compact: {
            type: Boolean,
            default: false,
        },
        clearTitle: {
            type: String,
            default: "",
        },
        loading: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["update:modelValue", "clear"],
    methods: {
        clear() {
            this.$emit("update:modelValue", "");
            this.$emit("clear");
        },
    },
};
</script>
