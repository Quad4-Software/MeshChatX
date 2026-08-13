<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col items-center justify-center px-4 py-10 text-center" :class="rootClass">
        <MaterialDesignIcon icon-name="loading" class="size-8 animate-spin text-blue-500 dark:text-blue-400" />
        <p v-if="message" class="mt-3 text-sm text-gray-600 dark:text-gray-400">{{ message }}</p>
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

export default {
    name: "LoadingState",
    components: {
        MaterialDesignIcon,
    },
    props: {
        message: {
            type: String,
            default: "",
        },
        rootClass: {
            type: String,
            default: "",
        },
    },
};
</script>
