<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <Teleport to="body">
        <div
            v-if="modelValue"
            class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
            @click.self="close"
        >
            <div
                class="w-full max-w-lg bg-sem-surface rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
            >
                <div class="px-6 py-4 border-b border-sem-border flex items-center justify-between">
                    <div class="flex items-center gap-2 min-w-0">
                        <MaterialDesignIcon icon-name="satellite-variant" class="size-6 text-sem-accent shrink-0" />
                        <h3 class="text-lg font-bold text-sem-fg truncate">
                            {{ $t("messages.telemetry_history_modal_title") }}
                        </h3>
                    </div>
                    <button
                        type="button"
                        class="text-sem-fg-muted hover:text-sem-fg-muted dark:hover:text-sem-fg-secondary transition-colors shrink-0"
                        @click="close"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto p-4 space-y-3">
                    <div v-if="telemetryItems.length === 0" class="text-center py-8 text-sem-fg-muted">
                        {{ $t("messages.telemetry_history_empty") }}
                    </div>
                    <TelemetryHistoryListItem
                        v-for="item in telemetryItems"
                        :key="item.lxmf_message.hash"
                        :item="item"
                        :format-time-ago="formatTimeAgo"
                        @location-click="emit('location-click', $event)"
                    />
                </div>
                <div
                    class="flex flex-col gap-3 border-t border-sem-border bg-sem-surface-muted/40 px-6 py-4 dark:bg-sem-surface"
                >
                    <TelemetryBatteryChart
                        v-if="batteryHistory.length > 1"
                        :samples="batteryHistory"
                        :id-suffix="gradientIdSuffix"
                    />

                    <div
                        class="flex w-full items-center justify-between gap-3"
                        :class="batteryHistory.length > 1 ? 'border-t border-sem-border/80 pt-3' : ''"
                    >
                        <label class="flex items-center gap-2 cursor-pointer group min-w-0">
                            <input
                                :checked="showTelemetryInChat"
                                type="checkbox"
                                class="rounded-sm border-sem-border text-sem-accent focus:ring-sem-focus shrink-0"
                                @change="onShowTelemetryChange"
                            />
                            <span
                                class="text-xs font-medium text-sem-fg-muted group-hover:text-sem-fg dark:group-hover:text-sem-fg"
                                >{{ $t("messages.telemetry_show_in_chat") }}</span
                            >
                        </label>
                        <button
                            type="button"
                            class="px-4 py-2 bg-sem-action-primary text-sem-action-primary-text text-xs font-bold rounded-lg hover:bg-sem-action-primary-hover transition-colors shadow-xs shrink-0"
                            @click="close"
                        >
                            {{ $t("messages.telemetry_history_done") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import TelemetryBatteryChart from "./TelemetryBatteryChart.vue";
import TelemetryHistoryListItem from "./TelemetryHistoryListItem.vue";
import { batteryHistoryFromTelemetryItems } from "../../../js/telemetryBatteryChartSpec.js";

const props = withDefaults(
    defineProps<{
        modelValue?: boolean;
        telemetryItems?: any[];
        showTelemetryInChat?: boolean;
        formatTimeAgo: (...args: any[]) => any;
        gradientIdSuffix?: string;
    }>(),
    {
        modelValue: false,
        telemetryItems: () => [],
        showTelemetryInChat: false,
        gradientIdSuffix: "peer",
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: boolean];
    "update:showTelemetryInChat": [value: boolean];
    "location-click": [item: any];
}>();

const batteryHistory = computed(() => batteryHistoryFromTelemetryItems(props.telemetryItems));

function close() {
    emit("update:modelValue", false);
}

function onShowTelemetryChange(e: Event) {
    emit("update:showTelemetryInChat", (e.target as HTMLInputElement).checked);
}
</script>
