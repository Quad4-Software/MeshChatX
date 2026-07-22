<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <label class="setting-toggle" :class="{ 'opacity-50 cursor-not-allowed': disabled }">
        <Toggle
            :id="id"
            :model-value="modelValue"
            :disabled="disabled"
            @update:model-value="$emit('update:modelValue', $event)"
        />
        <span class="setting-toggle__label">
            <span class="setting-toggle__title">{{ title }}</span>
            <span v-if="description" class="setting-toggle__description">
                <slot name="description">{{ description }}</slot>
            </span>
            <span v-if="hint" class="setting-toggle__hint">{{ hint }}</span>
        </span>
    </label>
</template>

<script>
import Toggle from "../forms/Toggle.vue";

export default {
    name: "SettingToggleRow",
    components: {
        Toggle,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        modelValue: {
            type: Boolean,
            default: false,
        },
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            default: "",
        },
        hint: {
            type: String,
            default: "",
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["update:modelValue"],
};
</script>
