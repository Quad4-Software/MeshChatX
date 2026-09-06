<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Svelte app shell. Boot component for the live UI.
     * Frame only: banners, auth gate, header, sidebar, page outlet, overlays.
     * Behaviour lives in lib/appShellState.svelte.ts and its helper modules.
     */
    import { onDestroy, onMount } from "svelte";
    import { t } from "../../js/i18n.js";
    import PageOutlet from "../../shell/PageOutlet.svelte";
    import { router } from "../../shell/hashRouter.js";
    import FatalErrorPage from "../fatal-error/FatalErrorPage.svelte";
    import AppShellBanners from "./components/AppShellBanners.svelte";
    import AppShellHeaderBar from "./components/AppShellHeaderBar.svelte";
    import AppShellSidebarPanel from "./components/AppShellSidebarPanel.svelte";
    import AppShellOverlays from "./components/AppShellOverlays.svelte";
    import { AppShellState } from "./lib/appShellState.svelte.js";
    import {
        onAutoRecoverDatabase,
        onDismissLanBindNoAuthBanner,
        onOpenBackupsForRecovery,
        onOpenInterfacesForRecovery,
        onOpenSettingsForRecovery,
        onRecoverNetwork,
        onRestartBackend,
        onViewBackendCrashReport,
    } from "./lib/appShellRecovery.js";

    const shell = new AppShellState();

    // t() is not reactive. Re-wrapping it when the locale changes makes every
    // template expression that calls tr() re-evaluate when locale changes.
    const tr = $derived.by(() => {
        void shell.localeVersion;
        return (key: string, values?: Record<string, unknown>) => t(key, values);
    });

    let middleEl: HTMLDivElement | undefined = $state();

    onMount(() => {
        shell.init();
    });

    onDestroy(() => {
        shell.destroy();
    });
</script>

<div
    class="h-dvh min-h-0 w-full flex flex-col transition-colors"
    class:dark={shell.isDarkTheme}
    style={shell.shellCanvasStyle}
>
    {#if shell.fatalError}
        <FatalErrorPage error={shell.fatalError} {router} />
    {/if}

    <AppShellBanners
        showEmergency={Boolean(shell.appInfo?.emergency)}
        emergencyLabel={tr("app.emergency_mode_active")}
        showDemo={shell.global.demoMode}
        demoLabel={tr("app.demo_mode_active")}
        showWsDisconnected={shell.showWsDisconnectedBanner}
        wsDisconnectedLabel={shell.backendOfflineBannerLabel}
        showBackendRecoveryActions={shell.showBackendRecoveryActions}
        backendRestarting={shell.backendRestarting}
        restartBackendLabel={tr("app.restart_backend")}
        viewBackendLogsLabel={tr("app.view_backend_logs")}
        showWsReconnected={shell.wsReconnectedBanner}
        wsReconnectedLabel={tr("app.backend_reconnected")}
        showNetworkStarting={shell.showNetworkStartingBanner}
        networkStartingLabel={tr("app.network_starting")}
        showLanBindNoAuth={shell.showLanBindNoAuthBanner}
        lanBindNoAuthLabel={tr("app.lan_bind_no_auth_banner")}
        dismissLanBindNoAuthLabel={tr("app.lan_bind_no_auth_dismiss")}
        showNetworkDegraded={shell.showNetworkDegradedBanner}
        networkDegradedLabel={shell.networkDegradedBannerLabel}
        networkRecovering={shell.networkRecovering}
        recoverNetworkLabel={tr("app.recover_network")}
        openSettingsLabel={tr("app.open_settings")}
        showOpenBackups={shell.showDatabaseRecoveryActions}
        openBackupsLabel={tr("app.open_backups")}
        autoRecoverLabel={tr("common.auto_recover")}
        autoRecovering={shell.databaseAutoRecovering}
        openInterfacesLabel={tr("app.open_interfaces")}
        onrestartbackend={() => void onRestartBackend(shell)}
        onviewbackendlogs={() => void onViewBackendCrashReport(shell)}
        onrecovernetwork={() => void onRecoverNetwork(shell)}
        onopensettings={() => onOpenSettingsForRecovery(shell)}
        ondismisslanbindnoauth={() => onDismissLanBindNoAuthBanner(shell)}
        onopenbackups={() => onOpenBackupsForRecovery(shell)}
        onautorecoverdatabase={() => void onAutoRecoverDatabase(shell)}
        onopeninterfaces={() => onOpenInterfacesForRecovery(shell)}
    />

    {#if shell.isAuthRoute}
        <PageOutlet />
    {:else if shell.showMainShell}
        {#if shell.isPopoutMode}
            <div class="flex flex-1 h-full w-full overflow-hidden transition-colors" style={shell.shellCanvasStyle}>
                <PageOutlet />
            </div>
        {:else}
            <AppShellHeaderBar {shell} {middleEl} />

            <div
                bind:this={middleEl}
                class="relative flex flex-1 w-full overflow-hidden transition-colors"
                style={shell.shellCanvasStyle}
            >
                {#if shell.isSidebarOpen}
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="absolute inset-0 z-65 bg-black/20 backdrop-blur-xs sm:hidden"
                        onclick={() => (shell.isSidebarOpen = false)}
                    ></div>
                {/if}

                <AppShellSidebarPanel {shell} />

                <div class="flex flex-1 min-w-0 overflow-hidden">
                    <PageOutlet />
                </div>
            </div>
        {/if}
    {/if}

    <AppShellOverlays {shell} />
</div>
