<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="absolute inset-0 z-20 flex items-center justify-center p-4">
        <div
            class="max-w-md bg-white dark:bg-zinc-900 p-6 rounded-xl shadow-xl border border-amber-200 dark:border-amber-900/50 flex flex-col items-center text-center space-y-4"
        >
            <MaterialDesignIcon icon-name="alert-circle" class="size-12 text-amber-500" />
            <p class="text-gray-900 dark:text-zinc-100 font-medium">{{ $t("map.no_map_loaded") }}</p>
            <button
                class="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-colors font-medium"
                @click="$emit('upload')"
            >
                {{ $t("map.upload_mbtiles") }}
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapNoMapWarning",
    components: { MaterialDesignIcon },
    emits: ["upload"],
};
</script>
