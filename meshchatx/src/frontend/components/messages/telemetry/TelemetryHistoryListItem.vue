<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="p-3 rounded-xl border border-gray-100 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/30">
        <div class="flex justify-between items-start mb-2">
            <span
                class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-gray-200 dark:bg-zinc-800 text-gray-600 dark:text-zinc-400"
            >
                {{ item.is_outbound ? $t("messages.telemetry_label_sent") : $t("messages.telemetry_label_received") }}
            </span>
            <span class="text-[10px] text-gray-400">{{ formatTimeAgo(item.lxmf_message.created_at) }}</span>
        </div>

        <div v-if="item.lxmf_message.fields?.telemetry?.location" class="flex items-center gap-2 mb-2">
            <button
                type="button"
                class="flex items-center gap-2 text-xs font-mono text-blue-600 dark:text-blue-400 hover:underline"
                @click="$emit('location-click', item.lxmf_message.fields.telemetry.location)"
            >
                <MaterialDesignIcon icon-name="map-marker" class="size-4" />
                {{ item.lxmf_message.fields.telemetry.location.latitude.toFixed(6) }},
                {{ item.lxmf_message.fields.telemetry.location.longitude.toFixed(6) }}
            </button>
        </div>

        <div
            v-if="item.lxmf_message.fields?.telemetry"
            class="flex flex-wrap gap-3 text-[10px] text-gray-500 dark:text-zinc-400"
        >
            <span v-if="item.lxmf_message.fields.telemetry.battery" class="flex items-center gap-1">
                <MaterialDesignIcon icon-name="battery" class="size-3" />
                {{
                    $t("messages.telemetry_battery_level", {
                        percent: item.lxmf_message.fields.telemetry.battery.charge_percent,
                    })
                }}
            </span>
            <span v-if="item.lxmf_message.fields.telemetry.physical_link" class="flex items-center gap-1">
                <MaterialDesignIcon icon-name="antenna" class="size-3" />
                {{ $t("messages.telemetry_snr_db", { snr: item.lxmf_message.fields.telemetry.physical_link.snr }) }}
            </span>
        </div>

        <div
            v-if="item.lxmf_message.fields?.commands?.some((c) => c['0x01'])"
            class="flex items-center gap-2 text-[10px] text-emerald-600 dark:text-emerald-400 mt-1"
        >
            <MaterialDesignIcon icon-name="crosshairs-question" class="size-3" />
            <span>{{ $t("messages.telemetry_location_request") }}</span>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "TelemetryHistoryListItem",
    components: { MaterialDesignIcon },
    props: {
        item: {
            type: Object,
            required: true,
        },
        formatTimeAgo: {
            type: Function,
            required: true,
        },
    },
    emits: ["location-click"],
};
</script>
