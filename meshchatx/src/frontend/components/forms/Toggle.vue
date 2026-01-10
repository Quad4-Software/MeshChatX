<template>
    <label
        :for="id"
        class="relative inline-flex items-center"
        :class="disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'"
    >
        <input
            :id="id"
            type="checkbox"
            :checked="modelValue"
            :disabled="disabled"
            class="sr-only peer"
            @change="!disabled && $emit('update:modelValue', $event.target.checked)"
        />
        <div
            class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600 dark:peer-checked:bg-blue-600"
        ></div>
        <span v-if="label" class="ml-3 text-sm font-medium text-gray-900 dark:text-gray-300">{{ label }}</span>
    </label>
</template>

<script>
export default {
    name: "Toggle",
    props: {
        id: {
            type: String,
            required: true,
        },
        modelValue: {
            type: Boolean,
            default: false,
        },
        label: {
            type: String,
            default: null,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["update:modelValue"],
};
</script>
