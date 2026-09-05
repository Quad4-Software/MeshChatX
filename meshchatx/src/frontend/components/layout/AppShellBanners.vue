<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import AppShellBannersSvelte from "../../features/app-shell/components/AppShellBanners.svelte";

/**
 * Thin Vue host for the Svelte AppShellBanners.
 */
export default {
    name: "AppShellBanners",
    props: {
        showEmergency: { type: Boolean, default: false },
        emergencyLabel: { type: String, default: "" },
        showDemo: { type: Boolean, default: false },
        demoLabel: { type: String, default: "" },
        showWsDisconnected: { type: Boolean, default: false },
        wsDisconnectedLabel: { type: String, default: "" },
        showBackendRecoveryActions: { type: Boolean, default: false },
        backendRestarting: { type: Boolean, default: false },
        restartBackendLabel: { type: String, default: "" },
        viewBackendLogsLabel: { type: String, default: "" },
        showWsReconnected: { type: Boolean, default: false },
        wsReconnectedLabel: { type: String, default: "" },
        showNetworkStarting: { type: Boolean, default: false },
        networkStartingLabel: { type: String, default: "" },
        showLanBindNoAuth: { type: Boolean, default: false },
        lanBindNoAuthLabel: { type: String, default: "" },
        dismissLanBindNoAuthLabel: { type: String, default: "" },
        showNetworkDegraded: { type: Boolean, default: false },
        networkDegradedLabel: { type: String, default: "" },
        networkRecovering: { type: Boolean, default: false },
        recoverNetworkLabel: { type: String, default: "" },
        openSettingsLabel: { type: String, default: "" },
        showOpenBackups: { type: Boolean, default: false },
        openBackupsLabel: { type: String, default: "" },
        autoRecoverLabel: { type: String, default: "" },
        autoRecovering: { type: Boolean, default: false },
        openInterfacesLabel: { type: String, default: "" },
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
    mounted() {
        this.remount();
    },
    updated() {
        this.remount();
    },
    beforeUnmount() {
        this.teardown();
    },
    methods: {
        teardown() {
            if (this._svelte) {
                unmount(this._svelte);
                this._svelte = null;
            }
        },
        remount() {
            this.teardown();
            const root = this.$refs.root;
            if (!root) return;
            this._svelte = mount(AppShellBannersSvelte, {
                target: root,
                props: {
                    showEmergency: this.showEmergency,
                    emergencyLabel: this.emergencyLabel,
                    showDemo: this.showDemo,
                    demoLabel: this.demoLabel,
                    showWsDisconnected: this.showWsDisconnected,
                    wsDisconnectedLabel: this.wsDisconnectedLabel,
                    showBackendRecoveryActions: this.showBackendRecoveryActions,
                    backendRestarting: this.backendRestarting,
                    restartBackendLabel: this.restartBackendLabel,
                    viewBackendLogsLabel: this.viewBackendLogsLabel,
                    showWsReconnected: this.showWsReconnected,
                    wsReconnectedLabel: this.wsReconnectedLabel,
                    showNetworkStarting: this.showNetworkStarting,
                    networkStartingLabel: this.networkStartingLabel,
                    showLanBindNoAuth: this.showLanBindNoAuth,
                    lanBindNoAuthLabel: this.lanBindNoAuthLabel,
                    dismissLanBindNoAuthLabel: this.dismissLanBindNoAuthLabel,
                    showNetworkDegraded: this.showNetworkDegraded,
                    networkDegradedLabel: this.networkDegradedLabel,
                    networkRecovering: this.networkRecovering,
                    recoverNetworkLabel: this.recoverNetworkLabel,
                    openSettingsLabel: this.openSettingsLabel,
                    showOpenBackups: this.showOpenBackups,
                    openBackupsLabel: this.openBackupsLabel,
                    autoRecoverLabel: this.autoRecoverLabel,
                    autoRecovering: this.autoRecovering,
                    openInterfacesLabel: this.openInterfacesLabel,
                    onrestartbackend: () => this.$emit("restart-backend"),
                    onviewbackendlogs: () => this.$emit("view-backend-logs"),
                    onrecovernetwork: () => this.$emit("recover-network"),
                    onopensettings: () => this.$emit("open-settings"),
                    ondismisslanbindnoauth: () => this.$emit("dismiss-lan-bind-no-auth"),
                    onopenbackups: () => this.$emit("open-backups"),
                    onautorecoverdatabase: () => this.$emit("auto-recover-database"),
                    onopeninterfaces: () => this.$emit("open-interfaces"),
                },
            });
        },
    },
};
</script>
