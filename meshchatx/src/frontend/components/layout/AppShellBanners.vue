<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div>
        <div
            v-if="showEmergency"
            class="relative z-100 bg-red-600 text-white px-4 py-2 text-center text-sm font-bold shadow-md animate-pulse"
        >
            <div class="flex items-center justify-center gap-2">
                <MaterialDesignIcon icon-name="alert-decagram" class="size-5" />
                <span>{{ emergencyLabel }}</span>
            </div>
        </div>

        <div
            v-if="showWsDisconnected"
            class="relative z-100 bg-red-700 text-white px-4 py-3 text-center text-sm font-medium shadow-md border-b border-red-800/80"
            role="status"
            aria-live="polite"
        >
            <p>{{ wsDisconnectedLabel }}</p>
            <div v-if="showBackendRecoveryActions" class="mt-2 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25 disabled:opacity-60"
                    :disabled="backendRestarting"
                    @click="$emit('restart-backend')"
                >
                    {{ restartBackendLabel }}
                </button>
                <button
                    type="button"
                    class="rounded-md bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20"
                    @click="$emit('view-backend-logs')"
                >
                    {{ viewBackendLogsLabel }}
                </button>
            </div>
        </div>
        <div
            v-if="showWsReconnected"
            class="relative z-100 bg-emerald-700 text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-emerald-800/80 transition-opacity duration-300"
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
        showBackendRecoveryActions: {
            type: Boolean,
            default: false,
        },
        backendRestarting: {
            type: Boolean,
            default: false,
        },
        restartBackendLabel: {
            type: String,
            default: "",
        },
        viewBackendLogsLabel: {
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
    emits: ["restart-backend", "view-backend-logs"],
};
</script>
