<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute bottom-4 right-4 z-20 w-72 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 p-4 space-y-3 animate-in slide-in-from-bottom-4"
    >
        <div class="flex justify-between items-center">
            <span class="font-bold text-sm text-gray-900 dark:text-zinc-100">{{
                status.status === "completed" ? $t("map.download_ready") : $t("map.exporting")
            }}</span>
            <button
                v-if="status.status === 'completed' || status.status === 'failed'"
                class="text-gray-400"
                @click="$emit('dismiss')"
            >
                <MaterialDesignIcon icon-name="close" class="size-4" />
            </button>
            <button
                v-else
                class="text-xs font-bold text-red-500 hover:text-red-600 uppercase tracking-tighter"
                @click="$emit('cancel')"
            >
                {{ $t("common.cancel") }}
            </button>
        </div>

        <div v-if="status.status !== 'completed' && status.status !== 'failed'">
            <div class="w-full h-2 bg-gray-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                <div
                    class="h-full bg-blue-500 transition-all duration-300"
                    :style="{ width: status.progress + '%' }"
                ></div>
            </div>
            <div class="flex justify-between text-[10px] text-gray-500 mt-1 uppercase font-bold tracking-wider">
                <span>{{ status.current }} / {{ status.total }} tiles</span>
                <span>{{ status.progress }}%</span>
            </div>
        </div>

        <div v-if="status.status === 'completed'" class="flex flex-col gap-2">
            <a
                :href="`/api/v1/map/export/${exportId}/download`"
                class="flex items-center justify-center space-x-2 w-full py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-bold transition-colors shadow-md text-xs"
            >
                <MaterialDesignIcon icon-name="download" class="size-4" />
                <span>{{ $t("map.download_now") }}</span>
            </a>
            <button
                class="flex items-center justify-center space-x-2 w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-bold transition-colors shadow-md text-xs"
                @click="$emit('show-offline-maps')"
            >
                <MaterialDesignIcon icon-name="map-check" class="size-4" />
                <span>Show in Offline Maps</span>
            </button>
        </div>

        <div v-if="status.status === 'failed'" class="text-xs text-red-500 bg-red-50 dark:bg-red-950/20 p-2 rounded-lg">
            {{ status.error }}
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapExportProgressPanel",
    components: { MaterialDesignIcon },
    props: {
        status: { type: Object, required: true },
        exportId: { type: [String, Number], default: null },
    },
    emits: ["dismiss", "cancel", "show-offline-maps"],
};
</script>
