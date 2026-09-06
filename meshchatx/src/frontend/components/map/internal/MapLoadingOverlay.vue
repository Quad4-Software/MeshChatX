<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="absolute inset-0 z-20 flex items-center justify-center bg-sem-canvas/50 backdrop-blur-xs">
        <div class="bg-sem-surface p-6 rounded-xl shadow-xl flex flex-col items-center space-y-4">
            <div class="animate-spin rounded-full h-12 w-12 border-4 border-sem-accent border-t-transparent"></div>
            <p class="text-sem-fg font-medium">{{ message || $t("map.uploading") }}</p>
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
