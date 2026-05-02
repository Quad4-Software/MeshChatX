<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute bottom-4 left-4 right-4 sm:left-4 sm:right-auto sm:w-80 md:max-lg:w-72 lg:w-80 z-20 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden text-gray-900 dark:text-zinc-100"
    >
        <div class="p-4 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div
                    v-if="marker.telemetry || marker.peer"
                    class="size-8 rounded-full flex items-center justify-center border-2"
                    :style="{
                        color: marker.peer?.lxmf_user_icon?.foreground_colour || '#3b82f6',
                        borderColor: marker.peer?.lxmf_user_icon?.foreground_colour || '#3b82f6',
                        backgroundColor: marker.peer?.lxmf_user_icon?.background_colour || '#ffffff',
                    }"
                >
                    <v-icon :icon="'mdi-' + (marker.peer?.lxmf_user_icon?.icon_name || 'account')" size="18"></v-icon>
                </div>
                <div
                    v-else-if="marker.discovered"
                    class="size-8 rounded-full flex items-center justify-center border-2 border-emerald-500 bg-emerald-50 text-emerald-600"
                >
                    <MaterialDesignIcon :icon-name="getDiscoveredIconName(marker.discovered)" class="size-[18px]" />
                </div>
                <div>
                    <h3 class="font-bold text-gray-900 dark:text-zinc-100 truncate w-40">
                        {{
                            marker.discovered?.name ||
                            marker.peer?.display_name ||
                            marker.telemetry?.destination_hash.substring(0, 8)
                        }}
                    </h3>
                    <div v-if="marker.telemetry" class="text-[10px] font-mono text-gray-500 uppercase tracking-tighter">
                        {{ marker.telemetry.destination_hash }}
                    </div>
                    <div
                        v-else-if="marker.discovered"
                        class="text-[10px] font-mono text-gray-500 uppercase tracking-tighter"
                    >
                        Discovered Interface
                    </div>
                </div>
            </div>
            <div class="flex items-center gap-1">
                <button
                    v-if="marker.telemetry"
                    class="p-2 rounded-full transition-colors"
                    :class="
                        marker.telemetry.is_tracking
                            ? 'text-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300'
                    "
                    :title="marker.telemetry.is_tracking ? 'Stop Tracking' : 'Live Track Peer'"
                    @click="$emit('toggle-tracking', marker.telemetry.destination_hash)"
                >
                    <v-icon :icon="marker.telemetry.is_tracking ? 'mdi-radar' : 'mdi-crosshairs'" size="20"></v-icon>
                </button>
                <button class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300 p-1" @click="$emit('close')">
                    <v-icon icon="mdi-close" size="20"></v-icon>
                </button>
            </div>
        </div>
        <div class="p-4 space-y-3">
            <div v-if="marker.discovered" class="space-y-3">
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Latitude</div>
                        <div class="tabular-nums">{{ marker.discovered.latitude.toFixed(6) }}</div>
                    </div>
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Longitude</div>
                        <div class="tabular-nums">{{ marker.discovered.longitude.toFixed(6) }}</div>
                    </div>
                </div>

                <div class="pt-2 border-t border-gray-100 dark:border-zinc-800 space-y-2">
                    <div v-if="marker.discovered.interface" class="flex justify-between items-center">
                        <span class="text-[10px] font-bold text-gray-400 uppercase">Interface</span>
                        <span class="text-xs font-mono">{{ marker.discovered.interface }}</span>
                    </div>
                    <div v-if="marker.discovered.via" class="flex justify-between items-center">
                        <span class="text-[10px] font-bold text-gray-400 uppercase">Via</span>
                        <span class="text-xs font-mono">{{ marker.discovered.via }}</span>
                    </div>
                    <div v-if="marker.discovered.hops != null" class="flex justify-between items-center">
                        <span class="text-[10px] font-bold text-gray-400 uppercase">Hops</span>
                        <span class="text-xs">{{ marker.discovered.hops }}</span>
                    </div>
                </div>
            </div>

            <div v-if="marker.telemetry" class="space-y-3">
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Latitude</div>
                        <div class="tabular-nums">
                            {{ marker.telemetry.telemetry.location.latitude.toFixed(6) }}
                        </div>
                    </div>
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Longitude</div>
                        <div class="tabular-nums">
                            {{ marker.telemetry.telemetry.location.longitude.toFixed(6) }}
                        </div>
                    </div>
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Altitude</div>
                        <div class="tabular-nums">{{ marker.telemetry.telemetry.location.altitude.toFixed(1) }}m</div>
                    </div>
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Speed</div>
                        <div class="tabular-nums">{{ marker.telemetry.telemetry.location.speed.toFixed(1) }}km/h</div>
                    </div>
                </div>

                <div v-if="marker.telemetry.physical_link" class="pt-2 border-t border-gray-100 dark:border-zinc-800">
                    <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Signal</div>
                    <div class="flex gap-4 text-xs font-mono">
                        <span>RSSI: {{ marker.telemetry.physical_link.rssi }}</span>
                        <span>SNR: {{ marker.telemetry.physical_link.snr }}</span>
                        <span>Q: {{ marker.telemetry.physical_link.q }}%</span>
                    </div>
                </div>

                <div class="pt-2 text-[10px] text-gray-400 flex items-center gap-1">
                    <v-icon icon="mdi-clock-outline" size="12"></v-icon>
                    Updated: {{ formatTimestamp(marker.telemetry.timestamp) }}
                </div>

                <div class="border-t border-gray-100 dark:border-zinc-800 pt-3">
                    <button
                        class="w-full py-2 bg-gray-100 hover:bg-gray-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-gray-700 dark:text-zinc-300 rounded-lg font-bold transition-all text-sm flex items-center justify-center gap-2 mb-2"
                        @click="$emit('toggle-mini-chat')"
                    >
                        <v-icon :icon="miniChatOpen ? 'mdi-chevron-up' : 'mdi-message-text'" size="16"></v-icon>
                        {{ miniChatOpen ? "Hide Mini-Chat" : "Show Mini-Chat" }}
                    </button>
                    <div v-if="miniChatOpen">
                        <MiniChat :destination-hash="marker.telemetry.destination_hash" />
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import MiniChat from "../MiniChat.vue";
import { getDiscoveredIconName } from "./discoveredIcons.js";

export default {
    name: "MapMarkerPanel",
    components: { MaterialDesignIcon, MiniChat },
    props: {
        marker: { type: Object, required: true },
        miniChatOpen: { type: Boolean, default: false },
    },
    emits: ["close", "toggle-tracking", "toggle-mini-chat"],
    methods: {
        getDiscoveredIconName,
        formatTimestamp(ts) {
            return new Date(ts * 1000).toLocaleString();
        },
    },
};
</script>
