<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div>
        <div
            v-if="showEmergency"
            class="relative z-[100] bg-red-600 text-white px-4 py-2 text-center text-sm font-bold shadow-md animate-pulse"
        >
            <div class="flex items-center justify-center gap-2">
                <MaterialDesignIcon icon-name="alert-decagram" class="size-5" />
                <span>{{ emergencyLabel }}</span>
            </div>
        </div>

        <div
            v-if="showWsDisconnected"
            class="relative z-[100] bg-red-700 text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-red-800/80"
            role="status"
            aria-live="polite"
        >
            {{ wsDisconnectedLabel }}
        </div>
        <div
            v-if="showWsReconnected"
            class="relative z-[100] bg-emerald-700 text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-emerald-800/80 transition-opacity duration-300"
            role="status"
            aria-live="polite"
        >
            {{ wsReconnectedLabel }}
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "AppShellBanners",
    components: { MaterialDesignIcon },
    props: {
        showEmergency: {
            type: Boolean,
            default: false,
        },
        emergencyLabel: {
            type: String,
            default: "",
        },
        showWsDisconnected: {
            type: Boolean,
            default: false,
        },
        wsDisconnectedLabel: {
            type: String,
            default: "",
        },
        showWsReconnected: {
            type: Boolean,
            default: false,
        },
        wsReconnectedLabel: {
            type: String,
            default: "",
        },
    },
};
</script>
