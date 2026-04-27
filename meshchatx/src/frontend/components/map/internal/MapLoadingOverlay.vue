<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="absolute inset-0 z-20 flex items-center justify-center bg-white/50 dark:bg-black/50 backdrop-blur-xs">
        <div class="bg-white dark:bg-zinc-900 p-6 rounded-xl shadow-xl flex flex-col items-center space-y-4">
            <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
            <p class="text-gray-900 dark:text-zinc-100 font-medium">{{ message || $t("map.uploading") }}</p>
        </div>
    </div>
</template>

<script>
export default {
    name: "MapLoadingOverlay",
    props: {
        message: { type: String, default: null },
    },
};
</script>
