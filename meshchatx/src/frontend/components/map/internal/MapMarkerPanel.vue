<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute bottom-4 left-4 right-4 sm:left-4 sm:right-auto sm:w-80 md:max-lg:w-72 lg:w-80 z-20 bg-sem-surface rounded-xl shadow-2xl border border-sem-border overflow-hidden text-sem-fg"
    >
        <div class="p-4 border-b border-sem-border flex items-center justify-between">
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
                    <MaterialDesignIcon
                        :icon-name="marker.peer?.lxmf_user_icon?.icon_name || 'account'"
                        class="size-[18px]"
                    />
                </div>
                <div
                    v-else-if="marker.discovered"
                    class="size-8 rounded-full flex items-center justify-center border-2 border-emerald-500 bg-emerald-50 text-emerald-600"
                >
                    <MaterialDesignIcon :icon-name="getDiscoveredIconName(marker.discovered)" class="size-[18px]" />
                </div>
                <div>
                    <h3 class="font-bold text-sem-fg truncate w-40">
                        {{
                            marker.discovered?.name ||
                            marker.peer?.display_name ||
                            shortHash(marker.telemetry?.destination_hash)
                        }}
                    </h3>
                    <div v-if="marker.telemetry" class="text-[10px] font-mono text-gray-500 uppercase tracking-tighter">
                        {{ marker.telemetry.destination_hash || "" }}
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
                            ? 'text-blue-500 bg-sem-surface-muted'
                            : 'text-sem-fg-muted hover:text-sem-fg'
                    "
                    :title="marker.telemetry.is_tracking ? 'Stop Tracking' : 'Live Track Peer'"
                    @click="$emit('toggle-tracking', marker.telemetry.destination_hash)"
                >
                    <MaterialDesignIcon
                        :icon-name="marker.telemetry.is_tracking ? 'radar' : 'crosshairs'"
                        class="size-5"
                    />
                </button>
                <button class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300 p-1" @click="$emit('close')">
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>
        </div>
        <div class="p-4 space-y-3">
            <div v-if="marker.discovered" class="space-y-3">
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Latitude</div>
                        <div class="tabular-nums">{{ formatFixed(marker.discovered.latitude, 6) }}</div>
                    </div>
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Longitude</div>
                        <div class="tabular-nums">{{ formatFixed(marker.discovered.longitude, 6) }}</div>
                    </div>
                </div>

                <div class="pt-2 border-t border-sem-border space-y-2">
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
                <div v-if="telemetryLocation" class="space-y-2 text-sm">
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                            {{ $t("map.coordinate_format") }}
                        </div>
                        <div class="tabular-nums break-all">{{ formattedTelemetryCoords }}</div>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                {{ $t("map.coord_lat") }}
                            </div>
                            <div class="tabular-nums">{{ formatFixed(telemetryLocation.latitude, 6) }}</div>
                        </div>
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                {{ $t("map.coord_lon") }}
                            </div>
                            <div class="tabular-nums">{{ formatFixed(telemetryLocation.longitude, 6) }}</div>
                        </div>
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                Altitude
                            </div>
                            <div class="tabular-nums">{{ formatFixed(telemetryLocation.altitude, 1) }}m</div>
                        </div>
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Speed</div>
                            <div class="tabular-nums">{{ formatFixed(telemetryLocation.speed, 1) }}km/h</div>
                        </div>
                    </div>
                </div>
                <div v-else class="text-[11px] text-sem-fg-muted">Location unavailable</div>

                <div v-if="marker.telemetry.physical_link" class="pt-2 border-t border-sem-border">
                    <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Signal</div>
                    <div class="flex gap-4 text-xs font-mono">
                        <span>RSSI: {{ marker.telemetry.physical_link.rssi }}</span>
                        <span>SNR: {{ marker.telemetry.physical_link.snr }}</span>
                        <span>Q: {{ marker.telemetry.physical_link.q }}%</span>
                    </div>
                </div>

                <div class="pt-2 text-[10px] text-gray-400 flex items-center gap-1">
                    <MaterialDesignIcon icon-name="clock-outline" class="size-3" />
                    Updated: {{ formatTimestamp(marker.telemetry.timestamp) }}
                </div>

                <div class="border-t border-sem-border pt-3">
                    <button
                        class="w-full py-2 bg-gray-100 hover:bg-gray-200 dark:bg-zinc-800 hover:bg-sem-surface-muted text-sem-fg-muted rounded-lg font-bold transition-all text-sm flex items-center justify-center gap-2 mb-2"
                        @click="$emit('toggle-mini-chat')"
                    >
                        <MaterialDesignIcon :icon-name="miniChatOpen ? 'chevron-up' : 'message-text'" class="size-4" />
                        {{ miniChatOpen ? "Hide Mini-Chat" : "Show Mini-Chat" }}
                    </button>
                    <div v-if="miniChatOpen && marker.telemetry.destination_hash">
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
import { formatCoordinate } from "../../../js/mapGeoCoords.js";

export default {
    name: "MapMarkerPanel",
    components: { MaterialDesignIcon, MiniChat },
    props: {
        marker: { type: Object, required: true },
        miniChatOpen: { type: Boolean, default: false },
        coordinateFormat: { type: String, default: "wgs84" },
    },
    emits: ["close", "toggle-tracking", "toggle-mini-chat"],
    computed: {
        telemetryLocation() {
            const loc = this.marker?.telemetry?.telemetry?.location;
            if (!loc || typeof loc !== "object") {
                return null;
            }
            if (loc.latitude == null || loc.longitude == null) {
                return null;
            }
            return loc;
        },
        formattedTelemetryCoords() {
            const loc = this.telemetryLocation;
            if (!loc) return "";
            const res = formatCoordinate(loc.longitude, loc.latitude, this.coordinateFormat);
            return res?.text || `${this.formatFixed(loc.latitude, 6)}, ${this.formatFixed(loc.longitude, 6)}`;
        },
    },
    methods: {
        getDiscoveredIconName,
        shortHash(hash) {
            const h = String(hash || "");
            return h ? h.substring(0, 8) : "Peer";
        },
        formatFixed(value, digits) {
            const n = Number(value);
            if (!Number.isFinite(n)) {
                return "-";
            }
            return n.toFixed(digits);
        },
        formatTimestamp(ts) {
            if (ts == null || !Number.isFinite(Number(ts))) {
                return "-";
            }
            return new Date(Number(ts) * 1000).toLocaleString();
        },
    },
};
</script>
