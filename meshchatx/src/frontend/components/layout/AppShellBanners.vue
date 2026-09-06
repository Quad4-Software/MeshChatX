<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div>
        <div
            v-if="showEmergency"
            class="relative z-100 bg-sem-danger text-white px-4 py-2 text-center text-sm font-bold shadow-md animate-pulse"
        >
            <div class="flex items-center justify-center gap-2">
                <MaterialDesignIcon icon-name="alert-decagram" class="size-5" />
                <span>{{ emergencyLabel }}</span>
            </div>
        </div>

        <div
            v-if="showDemo"
            class="relative z-100 bg-sem-warning text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-sem-warning/80"
            role="status"
        >
            {{ demoLabel }}
        </div>

        <div
            v-if="showWsDisconnected"
            class="relative z-100 bg-sem-danger text-white px-4 py-3 text-center text-sm font-medium shadow-md border-b border-sem-danger/80"
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
            class="relative z-100 bg-sem-success text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-sem-success/80 transition-opacity duration-300"
            role="status"
            aria-live="polite"
        >
            {{ wsReconnectedLabel }}
        </div>
        <div
            v-if="showNetworkStarting"
            class="relative z-100 bg-sem-info text-white px-4 py-2 text-center text-sm font-medium shadow-md border-b border-sem-info/80"
            role="status"
            aria-live="polite"
        >
            {{ networkStartingLabel }}
        </div>
        <div
            v-if="showLanBindNoAuth"
            class="relative z-100 bg-sem-warning text-white px-4 py-3 text-center text-sm font-medium shadow-md border-b border-sem-warning/80"
            role="status"
            aria-live="polite"
        >
            <p>{{ lanBindNoAuthLabel }}</p>
            <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25"
                    @click="$emit('open-settings')"
                >
                    {{ openSettingsLabel }}
                </button>
                <button
                    type="button"
                    class="rounded-md bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20"
                    @click="$emit('dismiss-lan-bind-no-auth')"
                >
                    {{ dismissLanBindNoAuthLabel }}
                </button>
            </div>
        </div>
        <div
            v-if="showNetworkDegraded"
            class="relative z-100 bg-sem-warning text-white px-4 py-3 text-center text-sm font-medium shadow-md border-b border-sem-warning/80"
            role="status"
            aria-live="polite"
        >
            <p>{{ networkDegradedLabel }}</p>
            <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25 disabled:opacity-60"
                    :disabled="networkRecovering"
                    @click="$emit('recover-network')"
                >
                    {{ recoverNetworkLabel }}
                </button>
                <button
                    v-if="!showOpenBackups"
                    type="button"
                    class="rounded-md bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20"
                    @click="$emit('open-settings')"
                >
                    {{ openSettingsLabel }}
                </button>
                <button
                    v-if="showOpenBackups"
                    type="button"
                    class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25 disabled:opacity-60"
                    :disabled="autoRecovering"
                    @click="$emit('auto-recover-database')"
                >
                    {{ autoRecoverLabel }}
                </button>
                <button
                    v-if="showOpenBackups"
                    type="button"
                    class="rounded-md bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25"
                    @click="$emit('open-backups')"
                >
                    {{ openBackupsLabel }}
                </button>
                <button
                    type="button"
                    class="rounded-md bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20"
                    @click="$emit('open-interfaces')"
                >
                    {{ openInterfacesLabel }}
                </button>
            </div>
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
        showDemo: {
            type: Boolean,
            default: false,
        },
        demoLabel: {
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
        showNetworkStarting: {
            type: Boolean,
            default: false,
        },
        networkStartingLabel: {
            type: String,
            default: "",
        },
        showLanBindNoAuth: {
            type: Boolean,
            default: false,
        },
        lanBindNoAuthLabel: {
            type: String,
            default: "",
        },
        dismissLanBindNoAuthLabel: {
            type: String,
            default: "",
        },
        showNetworkDegraded: {
            type: Boolean,
            default: false,
        },
        networkDegradedLabel: {
            type: String,
            default: "",
        },
        networkRecovering: {
            type: Boolean,
            default: false,
        },
        recoverNetworkLabel: {
            type: String,
            default: "",
        },
        openSettingsLabel: {
            type: String,
            default: "",
        },
        showOpenBackups: {
            type: Boolean,
            default: false,
        },
        openBackupsLabel: {
            type: String,
            default: "",
        },
        autoRecoverLabel: {
            type: String,
            default: "",
        },
        autoRecovering: {
            type: Boolean,
            default: false,
        },
        openInterfacesLabel: {
            type: String,
            default: "",
        },
    },
    emits: [
        "restart-backend",
        "view-backend-logs",
        "recover-network",
        "open-settings",
        "dismiss-lan-bind-no-auth",
        "open-backups",
        "auto-recover-database",
        "open-interfaces",
    ],
};
</script>
