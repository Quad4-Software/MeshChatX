<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Svelte app shell. Replaces components/App.vue as the boot component.
     * Template only. Behaviour lives in lib/appShellState.svelte.ts.
     */
    import { onDestroy, onMount } from "svelte";
    import { t } from "../../js/i18n.js";
    import logoUrl from "../../assets/images/logo.png";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import LanguageSelector from "../../ui/svelte/LanguageSelector.svelte";
    import Toast from "../../ui/svelte/Toast.svelte";
    import ConfirmDialog from "../../ui/svelte/ConfirmDialog.svelte";
    import PromptDialog from "../../ui/svelte/PromptDialog.svelte";
    import PageOutlet from "../../shell/PageOutlet.svelte";
    import { navigate, router } from "../../shell/hashRouter.js";
    import CallOverlay from "../call/components/CallOverlay.svelte";
    import FatalErrorPage from "../fatal-error/FatalErrorPage.svelte";
    import TutorialModalHost from "../tutorial/components/TutorialModalHost.svelte";
    import AppShellBanners from "./components/AppShellBanners.svelte";
    import AppIdentitySwitchOverlay from "./components/AppIdentitySwitchOverlay.svelte";
    import AppSidebarNav from "./components/AppSidebarNav.svelte";
    import AppSidebarClassicNav from "./components/AppSidebarClassicNav.svelte";
    import AppSidebarAccountFooter from "./components/AppSidebarAccountFooter.svelte";
    import AppSidebarClassicFooter from "./components/AppSidebarClassicFooter.svelte";
    import CommandPalette from "./components/CommandPalette.svelte";
    import IntegrityWarningModal from "./components/IntegrityWarningModal.svelte";
    import ChangelogModal from "./components/ChangelogModal.svelte";
    import ChannelPromptModal from "./components/ChannelPromptModal.svelte";
    import AndroidStorageChoicePrompt from "./components/AndroidStorageChoicePrompt.svelte";
    import PostInstallPromptHost from "./components/PostInstallPromptHost.svelte";
    import { AppShellState } from "./lib/appShellState.svelte.js";

    const shell = new AppShellState();

    let middleEl: HTMLDivElement | undefined = $state();
    let changelogModal: ReturnType<typeof ChangelogModal> | undefined = $state();
    let channelPromptModal: ReturnType<typeof ChannelPromptModal> | undefined = $state();
    let androidStoragePrompt: ReturnType<typeof AndroidStorageChoicePrompt> | undefined = $state();
    let postInstallHost: ReturnType<typeof PostInstallPromptHost> | undefined = $state();
    let commandPalette: ReturnType<typeof CommandPalette> | undefined = $state();
    let tutorialHost: ReturnType<typeof TutorialModalHost> | undefined = $state();

    $effect(() => {
        shell.hosts = {
            changelog: changelogModal ?? null,
            tutorial: tutorialHost ?? null,
            channelPrompt: channelPromptModal ?? null,
            androidStorage: androidStoragePrompt ?? null,
            postInstall: postInstallHost ?? null,
            commandPalette: commandPalette ?? null,
        };
    });

    onMount(() => {
        shell.init();
    });

    onDestroy(() => {
        shell.destroy();
    });

    function onCommandPaletteNavigate(route: unknown): void {
        void navigate(route as never);
    }
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
        emergencyLabel={t("app.emergency_mode_active")}
        showDemo={shell.global.demoMode}
        demoLabel={t("app.demo_mode_active")}
        showWsDisconnected={shell.showWsDisconnectedBanner}
        wsDisconnectedLabel={shell.backendOfflineBannerLabel}
        showBackendRecoveryActions={shell.showBackendRecoveryActions}
        backendRestarting={shell.backendRestarting}
        restartBackendLabel={t("app.restart_backend")}
        viewBackendLogsLabel={t("app.view_backend_logs")}
        showWsReconnected={shell.wsReconnectedBanner}
        wsReconnectedLabel={t("app.backend_reconnected")}
        showNetworkStarting={shell.showNetworkStartingBanner}
        networkStartingLabel={t("app.network_starting")}
        showLanBindNoAuth={shell.showLanBindNoAuthBanner}
        lanBindNoAuthLabel={t("app.lan_bind_no_auth_banner")}
        dismissLanBindNoAuthLabel={t("app.lan_bind_no_auth_dismiss")}
        showNetworkDegraded={shell.showNetworkDegradedBanner}
        networkDegradedLabel={shell.networkDegradedBannerLabel}
        networkRecovering={shell.networkRecovering}
        recoverNetworkLabel={t("app.recover_network")}
        openSettingsLabel={t("app.open_settings")}
        showOpenBackups={shell.showDatabaseRecoveryActions}
        openBackupsLabel={t("app.open_backups")}
        autoRecoverLabel={t("common.auto_recover")}
        autoRecovering={shell.databaseAutoRecovering}
        openInterfacesLabel={t("app.open_interfaces")}
        onrestartbackend={() => void shell.onRestartBackend()}
        onviewbackendlogs={() => void shell.onViewBackendCrashReport()}
        onrecovernetwork={() => void shell.onRecoverNetwork()}
        onopensettings={() => shell.onOpenSettingsForRecovery()}
        ondismisslanbindnoauth={() => shell.onDismissLanBindNoAuthBanner()}
        onopenbackups={() => shell.onOpenBackupsForRecovery()}
        onautorecoverdatabase={() => void shell.onAutoRecoverDatabase()}
        onopeninterfaces={() => shell.onOpenInterfacesForRecovery()}
    />

    {#if shell.isAuthRoute}
        <PageOutlet />
    {:else if shell.showMainShell}
        {#if shell.isPopoutMode}
            <div class="flex flex-1 h-full w-full overflow-hidden transition-colors" style={shell.shellCanvasStyle}>
                <PageOutlet />
            </div>
        {:else}
            <div
                class="z-100 flex shrink-0 bg-sem-canvas border-sem-border border-b min-h-12 sm:min-h-14 shadow-xs transition-colors pt-[env(safe-area-inset-top,0px)]"
            >
                <div
                    class="flex w-full min-h-12 sm:min-h-14 items-center gap-0 overflow-x-auto no-scrollbar pl-2 pr-2 sm:ps-0 sm:pe-3"
                >
                    <button
                        type="button"
                        class="sm:hidden shrink-0 mr-2 inline-flex min-h-[44px] min-w-[44px] items-center justify-center text-sem-fg-muted hover:text-sem-fg"
                        onclick={() => (shell.isSidebarOpen = !shell.isSidebarOpen)}
                    >
                        <MaterialDesignIcon iconName={shell.isSidebarOpen ? "close" : "menu"} class="size-6" />
                    </button>
                    <div class="flex min-w-0 flex-1 items-center gap-2 sm:flex-initial sm:gap-3">
                        <div class="hidden shrink-0 justify-start sm:flex sm:w-12 sm:justify-center">
                            <button
                                type="button"
                                class="flex h-10 w-10 cursor-pointer items-center justify-center overflow-hidden rounded-xl sm:h-12 sm:w-12"
                                onclick={() => shell.onAppNameClick(middleEl)}
                            >
                                <img
                                    class="h-9 w-9 max-h-full max-w-full object-contain sm:h-11 sm:w-11"
                                    src={logoUrl}
                                    alt=""
                                />
                            </button>
                        </div>
                        <div class="hidden min-w-0 leading-tight sm:block">
                            <button
                                type="button"
                                class="block text-left font-semibold cursor-pointer text-sem-fg hover:text-sem-accent transition-colors tracking-tight text-base"
                                onclick={() => shell.onAppNameClick(middleEl)}
                            >
                                {t("app.name")}
                            </button>
                            <div class="text-xs text-sem-fg-muted">
                                {t("app.tagline")}
                            </div>
                        </div>
                    </div>
                    <div class="flex ml-auto shrink-0 items-center mr-0 sm:mr-2 space-x-1 sm:space-x-2">
                        <button
                            type="button"
                            class="relative hidden sm:inline-flex rounded-full p-1.5 text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                            title={shell.themeToggleTitle}
                            onclick={() => void shell.toggleTheme()}
                        >
                            <MaterialDesignIcon iconName={shell.themeToggleIcon} class="w-5 h-5" />
                        </button>
                        <LanguageSelector
                            class="hidden sm:block"
                            onlanguagechange={(code) => void shell.onLanguageChange(code)}
                        />
                        <button
                            type="button"
                            class="hidden sm:inline-flex rounded-full p-1.5 text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                            title={t("command_palette.open_hint")}
                            aria-label={t("command_palette.open_hint")}
                            data-testid="header-command-palette"
                            onclick={() => shell.openCommandPalette()}
                        >
                            <MaterialDesignIcon iconName="magnify" class="w-5 h-5" />
                        </button>
                        {#if shell.rrcEnabled}
                            <button
                                type="button"
                                class="relative inline-flex rounded-full p-2 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 sm:p-1.5 items-center justify-center text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                                title={t("app.relay_chat")}
                                aria-label={t("app.relay_chat")}
                                data-testid="header-relay-chat"
                                onclick={() => void navigate({ name: "relay-chat" })}
                            >
                                <MaterialDesignIcon iconName="forum" class="w-5 h-5" />
                                {#if shell.global.relayChatUnreadCount > 0}
                                    <span
                                        class="absolute -top-0.5 -right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white"
                                    >
                                        {shell.global.relayChatUnreadCount > 99
                                            ? "99+"
                                            : shell.global.relayChatUnreadCount}
                                    </span>
                                {/if}
                            </button>
                        {/if}
                        <button
                            type="button"
                            class="relative inline-flex rounded-full p-2 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 sm:p-1.5 items-center justify-center text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                            title={t("app.audio_calls")}
                            aria-label={t("app.audio_calls")}
                            data-testid="header-telephone"
                            onclick={() => void navigate({ name: "call" })}
                        >
                            <MaterialDesignIcon iconName="phone" class="w-5 h-5" />
                            {#if shell.global.missedCallsCount > 0}
                                <span
                                    class="absolute -top-0.5 -right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white"
                                >
                                    {shell.global.missedCallsCount > 99 ? "99+" : shell.global.missedCallsCount}
                                </span>
                            {/if}
                        </button>
                        <button
                            type="button"
                            class="sm:hidden rounded-full p-2 min-h-[44px] min-w-[44px] inline-flex items-center justify-center text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                            title={shell.isSyncingPropagationNode ? t("app.syncing") : t("app.sync_messages")}
                            onclick={() => void shell.syncPropagationNode()}
                        >
                            <MaterialDesignIcon
                                iconName="refresh"
                                class="w-5 h-5 {shell.isSyncingPropagationNode ? 'animate-spin' : ''}"
                            />
                        </button>
                        {#if shell.inboundDeliveryCount > 0}
                            <button
                                type="button"
                                class="sm:hidden rounded-full p-2 min-h-[44px] min-w-[44px] inline-flex items-center justify-center text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors"
                                title={t("app.cancel_inbound_deliveries")}
                                onclick={() => void shell.cancelInboundDeliveries()}
                            >
                                <MaterialDesignIcon iconName="close-circle-outline" class="w-5 h-5" />
                            </button>
                        {/if}
                        <button
                            type="button"
                            class="hidden sm:flex rounded-full"
                            onclick={() => void shell.syncPropagationNode()}
                        >
                            <span
                                class="flex text-sem-fg bg-sem-surface-raised border border-sem-border hover:border-sem-accent px-2.5 py-1 rounded-full shadow-xs transition"
                            >
                                <MaterialDesignIcon
                                    iconName="refresh"
                                    class="size-5 {shell.isSyncingPropagationNode ? 'animate-spin' : ''}"
                                />
                                <span class="hidden sm:inline-block my-auto mx-1 text-sm font-medium">
                                    {shell.isSyncingPropagationNode ? t("app.syncing") : t("app.sync_messages")}
                                </span>
                            </span>
                        </button>
                        {#if shell.inboundDeliveryCount > 0}
                            <button
                                type="button"
                                class="hidden sm:flex rounded-full"
                                onclick={() => void shell.cancelInboundDeliveries()}
                            >
                                <span
                                    class="flex text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/60 hover:border-amber-400 dark:hover:border-amber-500/60 px-2.5 py-1 rounded-full shadow-xs transition"
                                >
                                    <MaterialDesignIcon iconName="close-circle-outline" class="size-5" />
                                    <span class="hidden sm:inline-block my-auto mx-1 text-sm font-medium">
                                        {t("app.cancel_inbound_deliveries_count", {
                                            count: shell.inboundDeliveryCount,
                                        })}
                                    </span>
                                </span>
                            </button>
                        {/if}
                        <button
                            type="button"
                            class="inline-flex rounded-full min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 items-center justify-center"
                            title={t("app.compose")}
                            aria-label={t("app.compose")}
                            data-testid="header-compose"
                            onclick={() => void shell.composeNewMessage()}
                        >
                            <span
                                class="flex rounded-full border border-sem-action-primary bg-sem-action-primary px-2.5 py-1 text-white shadow-xs transition hover:bg-sem-action-primary-hover"
                            >
                                <span>
                                    <MaterialDesignIcon iconName="email" class="w-5 h-5" />
                                </span>
                                <span class="hidden sm:inline-block my-auto mx-1 text-sm font-semibold">
                                    {t("app.compose")}
                                </span>
                            </span>
                        </button>
                    </div>
                </div>
            </div>

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

                <div
                    class="absolute inset-y-0 left-0 z-70 transform transition-all duration-300 ease-in-out sm:relative sm:inset-auto sm:z-0 sm:flex sm:translate-x-0 {shell.isSidebarOpen
                        ? 'translate-x-0'
                        : '-translate-x-full'} {shell.isSidebarCollapsed ? 'w-14' : 'w-80 md:max-lg:w-64 lg:w-80'}"
                >
                    <div class="flex h-full w-full flex-col overflow-y-auto border-r border-sem-border bg-sem-canvas">
                        <!-- toggle row for desktop (h-10 aligns with Messages/Nomad collapse rows) -->
                        <div
                            class="h-10 shrink-0 items-center gap-1 border-b border-sem-border px-2 {shell.isSidebarNavEditing &&
                            !shell.isSidebarCollapsed
                                ? 'flex'
                                : 'hidden sm:flex'} {shell.isSidebarCollapsed ? 'justify-center' : 'justify-end'}"
                        >
                            {#if shell.isSidebarNavEditing && !shell.isSidebarCollapsed}
                                <button
                                    type="button"
                                    class="p-1.5 rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                                    data-testid="sidebar-nav-layout-save"
                                    title={t("common.save")}
                                    aria-label={t("common.save")}
                                    onclick={() => shell.saveSidebarNavLayout()}
                                >
                                    <MaterialDesignIcon iconName="content-save" class="size-5" />
                                </button>
                            {/if}
                            <button
                                type="button"
                                class="p-1.5 rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted transition-colors hidden sm:inline-flex"
                                onclick={() => shell.toggleSidebarCollapsed()}
                            >
                                <MaterialDesignIcon
                                    iconName={shell.isSidebarCollapsed ? "chevron-right" : "chevron-left"}
                                    class="size-5"
                                />
                            </button>
                        </div>

                        <!-- mobile-only quick settings row (theme + language) -->
                        <div
                            class="sm:hidden flex items-center justify-between gap-2 px-3 py-2 border-b border-sem-border"
                        >
                            <button
                                type="button"
                                class="flex items-center gap-2 flex-1 rounded-lg px-2 py-1.5 text-sm font-medium text-sem-fg hover:bg-sem-surface-muted transition-colors"
                                title={shell.themeToggleTitle}
                                onclick={() => void shell.toggleTheme()}
                            >
                                <MaterialDesignIcon iconName={shell.themeToggleIcon} class="w-5 h-5 shrink-0" />
                                <span class="truncate">{shell.themeToggleTitle}</span>
                            </button>
                            <LanguageSelector onlanguagechange={(code) => void shell.onLanguageChange(code)} />
                        </div>

                        {#if shell.useGroupedAppSidebar}
                            <AppSidebarNav
                                primaryNavGroups={shell.primaryNavGroups}
                                moreNavItems={shell.moreNavItems}
                                isCollapsed={shell.isSidebarCollapsed}
                                isEditing={shell.isSidebarNavEditing}
                                isShowingMoreNav={shell.isShowingMoreNav}
                                unreadConversationsCount={shell.global.unreadConversationsCount}
                                relayChatUnreadCount={shell.global.relayChatUnreadCount}
                                missedCallsCount={shell.global.missedCallsCount}
                                activeRouteName={shell.routeName}
                                onmoretoggle={() => shell.onMoreNavToggle()}
                                oneditstart={() => shell.enterSidebarNavEdit()}
                                onnavreorder={(op) => shell.onSidebarNavReorder(op)}
                            />
                        {:else}
                            <AppSidebarClassicNav
                                navItems={shell.visibleNavItems}
                                isCollapsed={shell.isSidebarCollapsed}
                                isEditing={shell.isSidebarNavEditing}
                                unreadConversationsCount={shell.global.unreadConversationsCount}
                                relayChatUnreadCount={shell.global.relayChatUnreadCount}
                                missedCallsCount={shell.global.missedCallsCount}
                                activeRouteName={shell.routeName}
                                oneditstart={() => shell.enterSidebarNavEdit()}
                                onnavreorder={(op) => shell.onSidebarNavReorder(op)}
                            />
                        {/if}

                        <div>
                            {#if shell.config && shell.useGroupedAppSidebar}
                                <AppSidebarAccountFooter
                                    config={shell.config}
                                    displayName={shell.displayName}
                                    identityLabel={shell.identitySidebarLabel}
                                    lastAnnouncedLabel={shell.lastAnnouncedSidebarLabel}
                                    isCollapsed={shell.isSidebarCollapsed}
                                    onupdatedisplayname={(value) => shell.onDisplayNameUpdate(value)}
                                    onsaveidentity={() => shell.flushIdentitySave()}
                                    onsendannounce={() => void shell.sendAnnounce()}
                                    onannounceintervalchange={(seconds) =>
                                        void shell.onAnnounceIntervalChange(seconds)}
                                    oncopyvalue={(value, label) => void shell.copyValue(value, label)}
                                    onopenlxmfqr={() => void shell.openLxmfQr()}
                                />
                            {:else if shell.config}
                                <AppSidebarClassicFooter
                                    config={shell.config}
                                    displayName={shell.displayName}
                                    identityLabel={shell.identitySidebarLabel}
                                    lastAnnouncedLabel={shell.lastAnnouncedSidebarLabel}
                                    isCollapsed={shell.isSidebarCollapsed}
                                    onupdatedisplayname={(value) => shell.onDisplayNameUpdate(value)}
                                    onsaveidentity={() => shell.flushIdentitySave()}
                                    onsendannounce={() => void shell.sendAnnounce()}
                                    onannounceintervalchange={(seconds) =>
                                        void shell.onAnnounceIntervalChange(seconds)}
                                    oncopyvalue={(value, label) => void shell.copyValue(value, label)}
                                    onopenlxmfqr={() => void shell.openLxmfQr()}
                                />
                            {/if}

                            {#if shell.appInfo?.version}
                                <div class="shrink-0 border-t border-sem-border bg-sem-canvas">
                                    <a
                                        href="#/about"
                                        class="flex items-center gap-2 py-2 text-[10px] font-mono text-gray-500 transition-colors hover:text-gray-700 text-sem-fg-muted dark:hover:text-zinc-300 {shell.isSidebarCollapsed
                                            ? 'justify-center px-0'
                                            : 'justify-start px-3'}"
                                        data-testid="sidebar-app-version"
                                        title={shell.sidebarVersionTitle}
                                    >
                                        {#if shell.isSidebarCollapsed}
                                            <MaterialDesignIcon iconName="information-outline" class="size-4" />
                                        {:else}
                                            <span>{shell.sidebarVersionLabel}</span>
                                            {#if shell.sidebarChannelLabel}
                                                <span
                                                    class="inline-flex h-4 items-center rounded-xs px-1.5 text-[9px] font-black uppercase tracking-tighter {shell.sidebarChannelBadgeClass}"
                                                    data-testid="sidebar-channel-badge"
                                                >
                                                    {shell.sidebarChannelLabel}
                                                </span>
                                            {/if}
                                        {/if}
                                    </a>
                                </div>
                            {/if}
                        </div>
                    </div>
                </div>

                <div class="flex flex-1 min-w-0 overflow-hidden">
                    <PageOutlet />
                </div>
            </div>
        {/if}
    {/if}

    {#if shell.shouldShowCallOverlay}
        <CallOverlay
            activeCall={shell.activeCall || shell.lastCall}
            isEnded={shell.isCallEnded}
            wasDeclined={shell.wasDeclined}
            voicemailStatus={shell.voicemailStatus}
            initiationStatus={shell.initiationStatus}
            initiationTargetHash={shell.initiationTargetHash}
            initiationTargetName={shell.initiationTargetName}
            {router}
            route={shell.route}
            onhangup={() => shell.onOverlayHangup()}
            ontogglemic={(muted) => shell.onToggleMic(muted)}
            ontogglespeaker={(muted) => shell.onToggleSpeaker(muted)}
        />
    {/if}

    <Toast />
    <ConfirmDialog />
    <PromptDialog />
    <CommandPalette bind:this={commandPalette} onnavigate={onCommandPaletteNavigate} />
    <IntegrityWarningModal />
    <ChangelogModal bind:this={changelogModal} appVersion={shell.appInfo?.version ?? ""} />
    <ChannelPromptModal bind:this={channelPromptModal} />
    <TutorialModalHost bind:this={tutorialHost} />
    <AndroidStorageChoicePrompt bind:this={androidStoragePrompt} variant="upgrade" />
    <PostInstallPromptHost bind:this={postInstallHost} />

    {#if shell.showLxmfQr}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="fixed inset-0 z-190 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
            onclick={(event) => {
                if (event.target === event.currentTarget) {
                    shell.showLxmfQr = false;
                }
            }}
        >
            <div class="w-full max-w-sm bg-sem-surface rounded-2xl shadow-2xl overflow-hidden">
                <div class="px-4 py-3 border-b border-sem-border flex items-center justify-between">
                    <h3 class="text-sm font-semibold text-sem-fg">Identity QR (LXMA)</h3>
                    <button
                        type="button"
                        class="text-sem-fg-muted hover:text-sem-fg transition-colors"
                        onclick={() => (shell.showLxmfQr = false)}
                    >
                        <MaterialDesignIcon iconName="close" class="size-5" />
                    </button>
                </div>
                <div class="p-4 space-y-3">
                    <div class="flex justify-center">
                        {#if shell.lxmfQrDataUrl}
                            <img
                                src={shell.lxmfQrDataUrl}
                                alt="LXMF QR"
                                class="w-48 h-48 bg-white rounded-xl border border-sem-border"
                            />
                        {/if}
                    </div>
                    {#if shell.config?.lxmf_address_hash}
                        <div class="text-xs font-mono text-sem-fg-secondary text-center wrap-break-word">
                            {shell.getMyIdentityUri()}
                        </div>
                    {/if}
                    <div class="flex justify-center">
                        <button
                            type="button"
                            class="px-3 py-1.5 text-xs font-semibold text-sem-accent hover:underline"
                            onclick={() => void shell.copyIdentityUri()}
                        >
                            {t("common.copy")}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    {/if}

    <AppIdentitySwitchOverlay show={shell.isSwitchingIdentity} {logoUrl} />
</div>
