<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import AppShellBannersSvelte from "../../features/app-shell/components/AppShellBanners.svelte";
import { createThinSvelteHost } from "../../js/svelteVueHost";

const svelteHost = createThinSvelteHost({
    component: AppShellBannersSvelte,
    buildProps(vm) {
        return {
            showEmergency: vm.showEmergency,
            emergencyLabel: vm.emergencyLabel,
            showDemo: vm.showDemo,
            demoLabel: vm.demoLabel,
            showWsDisconnected: vm.showWsDisconnected,
            wsDisconnectedLabel: vm.wsDisconnectedLabel,
            showBackendRecoveryActions: vm.showBackendRecoveryActions,
            backendRestarting: vm.backendRestarting,
            restartBackendLabel: vm.restartBackendLabel,
            viewBackendLogsLabel: vm.viewBackendLogsLabel,
            showWsReconnected: vm.showWsReconnected,
            wsReconnectedLabel: vm.wsReconnectedLabel,
            showNetworkStarting: vm.showNetworkStarting,
            networkStartingLabel: vm.networkStartingLabel,
            showLanBindNoAuth: vm.showLanBindNoAuth,
            lanBindNoAuthLabel: vm.lanBindNoAuthLabel,
            dismissLanBindNoAuthLabel: vm.dismissLanBindNoAuthLabel,
            showNetworkDegraded: vm.showNetworkDegraded,
            networkDegradedLabel: vm.networkDegradedLabel,
            networkRecovering: vm.networkRecovering,
            recoverNetworkLabel: vm.recoverNetworkLabel,
            openSettingsLabel: vm.openSettingsLabel,
            showOpenBackups: vm.showOpenBackups,
            openBackupsLabel: vm.openBackupsLabel,
            autoRecoverLabel: vm.autoRecoverLabel,
            autoRecovering: vm.autoRecovering,
            openInterfacesLabel: vm.openInterfacesLabel,
            onrestartbackend: () => vm.$emit("restart-backend"),
            onviewbackendlogs: () => vm.$emit("view-backend-logs"),
            onrecovernetwork: () => vm.$emit("recover-network"),
            onopensettings: () => vm.$emit("open-settings"),
            ondismisslanbindnoauth: () => vm.$emit("dismiss-lan-bind-no-auth"),
            onopenbackups: () => vm.$emit("open-backups"),
            onautorecoverdatabase: () => vm.$emit("auto-recover-database"),
            onopeninterfaces: () => vm.$emit("open-interfaces"),
        };
    },
});

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
    ...svelteHost,
};
</script>
