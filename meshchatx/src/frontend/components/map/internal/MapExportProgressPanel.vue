<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute bottom-4 right-4 z-20 w-72 bg-sem-surface rounded-xl shadow-2xl border border-sem-border p-4 space-y-3 animate-in slide-in-from-bottom-4"
    >
        <div class="flex justify-between items-center">
            <span class="font-bold text-sm text-sem-fg">{{
                status.status === "completed" ? $t("map.download_ready") : $t("map.exporting")
            }}</span>
            <button
                v-if="status.status === 'completed' || status.status === 'failed'"
                class="text-sem-fg-muted"
                @click="emit('dismiss')"
            >
                <MaterialDesignIcon icon-name="close" class="size-4" />
            </button>
            <button
                v-else
                class="text-xs font-bold text-sem-danger hover:text-sem-danger uppercase tracking-tighter"
                @click="emit('cancel')"
            >
                {{ $t("common.cancel") }}
            </button>
        </div>

        <div v-if="status.status !== 'completed' && status.status !== 'failed'">
            <div class="w-full h-2 bg-sem-surface-muted rounded-full overflow-hidden">
                <div
                    class="h-full bg-sem-info transition-all duration-300"
                    :style="{ width: status.progress + '%' }"
                ></div>
            </div>
            <div class="flex justify-between text-[10px] text-sem-fg-muted mt-1 uppercase font-bold tracking-wider">
                <span>{{ status.current }} / {{ status.total }} tiles</span>
                <span>{{ status.progress }}%</span>
            </div>
        </div>

        <div v-if="status.status === 'completed'" class="flex flex-col gap-2">
            <a
                :href="`/api/v1/map/export/${exportId}/download`"
                class="flex items-center justify-center space-x-2 w-full py-2 bg-sem-success hover:bg-sem-success text-white rounded-lg font-bold transition-colors shadow-md text-xs"
            >
                <MaterialDesignIcon icon-name="download" class="size-4" />
                <span>{{ $t("map.download_now") }}</span>
            </a>
            <button
                class="flex items-center justify-center space-x-2 w-full py-2 bg-sem-info hover:bg-sem-action-primary text-sem-action-primary-text rounded-lg font-bold transition-colors shadow-md text-xs"
                @click="emit('show-offline-maps')"
            >
                <MaterialDesignIcon icon-name="map-check" class="size-4" />
                <span>Show in Offline Maps</span>
            </button>
        </div>

        <div
            v-if="status.status === 'failed'"
            class="text-xs text-sem-danger bg-sem-danger/15 dark:bg-sem-danger/15 p-2 rounded-lg"
        >
            {{ status.error }}
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from "vue";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import AndroidDownloadBridge from "../../../js/AndroidDownloadBridge";
import { translateUi } from "../../../js/localeLoader.js";

const props = withDefaults(
    defineProps<{
        status: Record<string, any>;
        exportId?: string | number | null;
    }>(),
    {
        exportId: null,
    }
);

const emit = defineEmits<{
    dismiss: [];
    cancel: [];
    "show-offline-maps": [];
}>();

const notificationId = computed(() => `map-export-${props.exportId}`);
const notificationName = computed(() => translateUi("map.exporting"));

watch(
    () => props.status.progress,
    (progress) => {
        if (props.status.status !== "completed" && props.status.status !== "failed") {
            AndroidDownloadBridge.notifyProgress(notificationId.value, notificationName.value, progress);
        }
    }
);

watch(
    () => props.status.status,
    (status) => {
        if (status === "completed") {
            AndroidDownloadBridge.cancelNotification(notificationId.value);
            AndroidDownloadBridge.sessionEnd(notificationId.value);
        } else if (status === "failed") {
            AndroidDownloadBridge.notifyFailed(notificationId.value, notificationName.value);
            AndroidDownloadBridge.sessionEnd(notificationId.value);
        }
    }
);

onMounted(() => {
    AndroidDownloadBridge.sessionStart(notificationId.value);
    if (props.status.status !== "completed" && props.status.status !== "failed") {
        AndroidDownloadBridge.notifyProgress(notificationId.value, notificationName.value, props.status.progress);
    }
});

onUnmounted(() => {
    AndroidDownloadBridge.cancelNotification(notificationId.value);
    AndroidDownloadBridge.sessionEnd(notificationId.value);
});
</script>
