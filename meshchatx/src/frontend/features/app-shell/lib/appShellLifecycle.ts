// SPDX-License-Identifier: 0BSD

/**
 * Shell boot, teardown, poll intervals, live transport, and WS handler registration.
 * Split out of appShellState so each module stays reviewable.
 */

import { watch } from "vue";
import LiveTransport from "../../../js/liveTransport.js";
import { installWsLiveSync } from "../../../js/wsLiveSync.js";
import GlobalState, { mergeGlobalConfig } from "../../../js/GlobalState.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import NotificationUtils from "../../../js/NotificationUtils.js";
import { listOpenDestinationHashes, subscribeOpenDestinationHashes } from "../../../js/activeConversationStore.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    CLIENT_HEAP_SAMPLE_INTERVAL_MS,
    MEMORY_WARNING_TOAST_KEY,
    evaluateClientHeapSample,
    markMemoryWarningDismissed,
    showMemoryWarningToastIfNeeded,
} from "../../../js/healthMemoryWarning.js";
import { t } from "../../../js/i18n.js";
import ElectronUtils from "../../../js/ElectronUtils.js";
import fatalErrorState from "../../../js/fatalErrorState.js";
import { loadFeatureSidebarCollapsed, saveFeatureSidebarCollapsed, clearMessagePanes } from "../../../js/browserLayoutStore.js";
import {
    applyNavLayout,
    captureNavLayout,
    cloneNavLayout,
    loadAppSidebarNavLayout,
    moveNavGroup,
    moveNavGroupByOffset,
    moveNavItem,
    moveNavItemByOffset,
    orderItemsByLayout,
    saveAppSidebarNavLayout,
} from "../../../js/appSidebarNavLayout.js";
import {
    applyBackgroundPollInterval,
    BATTERY_SAVER_CHANGED_EVENT,
    loadBatterySaverPrefs,
} from "../../../js/settings/batterySaverPrefs.js";
import {
    applyAppearanceTheme,
    resolveEffectiveTheme,
    shellCanvasBackgroundStyle,
    subscribeSystemTheme,
    systemPrefersDark,
} from "../../../theme/themeEngine.js";
import { navigate, router, subscribe as subscribeRoute } from "../../../shell/hashRouter.js";
import { handleProtocolLink } from "./appShellLinks.js";
import { apiClient, electronBridge } from "./appShellShared.js";
import { clearWsShellUiTimers, maybeNavigateNetworkRecovery, onBackendProcessExited, onWsShellReady, registerShellWsHandlers, resyncShellAfterWebsocketReconnect, unregisterShellWsHandlers } from "./appShellRecovery.js";
import { applyAppearanceThemeFromConfig, applyShellAppearance, getAppInfo, getBlockedDestinations, getConfig, getKeyboardShortcuts } from "./appShellConfig.js";
import { updateRelayChatUnreadCount, updateUnreadConversationsCount } from "./appShellNav.js";
import { updatePropagationNodeStatus } from "./appShellPropagation.js";
import { stopRingtone, updateRingtonePlayer, updateTelephoneStatus } from "./appShellTelephony.js";
import type { AppShellState } from "./appShellState.svelte.js";

export function syncGlobalMirror(state: AppShellState): void {
    state.global.authSessionResolved = GlobalState.authSessionResolved;
    state.global.authEnabled = GlobalState.authEnabled;
    state.global.authenticated = GlobalState.authenticated;
    state.global.isLoopbackBind = GlobalState.isLoopbackBind;
    state.global.demoMode = GlobalState.demoMode;
    state.global.networkDegraded = GlobalState.networkDegraded;
    state.global.networkDegradedError = GlobalState.networkDegradedError;
    state.global.networkStarting = GlobalState.networkStarting;
    state.global.networkReady = GlobalState.networkReady;
    state.global.unreadConversationsCount = GlobalState.unreadConversationsCount;
    state.global.relayChatUnreadCount = GlobalState.relayChatUnreadCount;
    state.global.missedCallsCount = GlobalState.missedCallsCount;
    state.global.activeCallTab = GlobalState.activeCallTab;
    state.global.rrcEnabled = GlobalState.config?.rrc_enabled !== false;
}

// Auth gate and shell start/stop
// ------------------------------------------------------------------
export function applyShellAuthState(state: AppShellState): void {
    if (!state.global.authSessionResolved) {
        return;
    }
    const needShell = !state.global.authEnabled || (state.global.authenticated && !state.isAuthRoute);
    if (needShell && !state.shellRunning) {
        if (state.global.networkStarting && !state.global.networkReady && !state.global.networkDegraded) {
            waitForMeshThenStartShell(state);
            return;
        }
        startShell(state);
    } else if (!needShell && state.shellRunning) {
        stopShell(state);
    }
}

export function waitForMeshThenStartShell(state: AppShellState): void {
    if (state.meshWaitStarted) {
        return;
    }
    state.meshWaitStarted = true;
    const stopWatch = watch(
        () => [GlobalState.networkReady, GlobalState.networkDegraded, GlobalState.networkStarting],
        () => {
            if (GlobalState.networkReady || GlobalState.networkDegraded || !GlobalState.networkStarting) {
                stopWatch();
                state.meshWaitStarted = false;
                if (!state.shellRunning) {
                    applyShellAuthState(state);
                }
            }
        },
        { immediate: true }
    );
}

export function startShell(state: AppShellState): void {
    if (state.shellRunning) {
        return;
    }
    state.shellRunning = true;
    state.wsLiveSyncHandle = installWsLiveSync({
        connection: LiveTransport,
        onNeedsResync: async () => {
            await resyncShellAfterWebsocketReconnect(state);
        },
    });
    LiveTransport.on("disconnected", state.onWsShellDisconnected);
    LiveTransport.on("connected", state.onWsShellConnected);
    LiveTransport.on("ready", state.onLiveTransportReady);
    LiveTransport.on("queue_expired", state.onLiveQueueExpired);
    LiveTransport.on("transport_fallback", state.onTransportFallback);
    void bootstrapLiveTransport(state);
    registerShellWsHandlers(state);
    startClientHeapMemoryWatch(state);
    GlobalEmitter.on("toast-dismissed", state.onToastDismissedShell);
    GlobalEmitter.on("identity-switching-start", state.onIdentitySwitchingStartShell);
    GlobalEmitter.on("identity-switching-abort", state.onIdentitySwitchingAbortShell);
    GlobalEmitter.on("identity-switched-apply", state.onIdentitySwitchedApplyShell);
    GlobalEmitter.on("sync-propagation-node", state.onSyncPropagationNodeShell);
    GlobalEmitter.on("config-updated", state.onConfigUpdatedExternally);
    GlobalEmitter.on("keyboard-shortcut", state.onKeyboardShortcutShell);
    GlobalEmitter.on("block-status-changed", state.onBlockStatusChangedShell);
    GlobalEmitter.on("show-changelog", state.onShowChangelogShell);
    GlobalEmitter.on("show-tutorial", state.onShowTutorialShell);
    GlobalEmitter.on("tutorial-finished", state.onTutorialFinishedShell);
    GlobalEmitter.on("changelog-closed", state.onChangelogClosedShell);
    GlobalEmitter.on("notifications-changed", state.updateUnreadConversationsCount);

    void getAppInfo(state);
    void getConfig(state);
    void getBlockedDestinations(state);
    void getKeyboardShortcuts(state);
    void updateRingtonePlayer(state);
    void updateTelephoneStatus(state);
    void updatePropagationNodeStatus(state);

    GlobalEmitter.on(BATTERY_SAVER_CHANGED_EVENT, state.onBatterySaverPrefsChangedShell);
    startShellPollIntervals(state);
    updateUnreadConversationsCount(state);
    updateRelayChatUnreadCount(state);
}

export function stopShell(state: AppShellState): void {
    if (!state.shellRunning) {
        return;
    }
    state.shellRunning = false;
    stopClientHeapMemoryWatch(state);
    GlobalEmitter.off("toast-dismissed", state.onToastDismissedShell);
    clearInterval(state.reloadInterval as ReturnType<typeof setInterval>);
    state.reloadInterval = null;
    clearInterval(state.appInfoInterval as ReturnType<typeof setInterval>);
    state.appInfoInterval = null;
    clearInterval(state.unreadCountInterval as ReturnType<typeof setInterval>);
    state.unreadCountInterval = null;
    GlobalEmitter.off(BATTERY_SAVER_CHANGED_EVENT, state.onBatterySaverPrefsChangedShell);
    LiveTransport.off("disconnected", state.onWsShellDisconnected);
    LiveTransport.off("connected", state.onWsShellConnected);
    LiveTransport.off("ready", state.onLiveTransportReady);
    LiveTransport.off("queue_expired", state.onLiveQueueExpired);
    LiveTransport.off("transport_fallback", state.onTransportFallback);
    if (state.wsLiveSyncHandle) {
        state.wsLiveSyncHandle.dispose();
        state.wsLiveSyncHandle = null;
    }
    unregisterShellWsHandlers(state);
    GlobalEmitter.off("identity-switching-start", state.onIdentitySwitchingStartShell);
    GlobalEmitter.off("identity-switching-abort", state.onIdentitySwitchingAbortShell);
    GlobalEmitter.off("identity-switched-apply", state.onIdentitySwitchedApplyShell);
    GlobalEmitter.off("sync-propagation-node", state.onSyncPropagationNodeShell);
    GlobalEmitter.off("config-updated", state.onConfigUpdatedExternally);
    GlobalEmitter.off("keyboard-shortcut", state.onKeyboardShortcutShell);
    GlobalEmitter.off("block-status-changed", state.onBlockStatusChangedShell);
    GlobalEmitter.off("show-changelog", state.onShowChangelogShell);
    GlobalEmitter.off("show-tutorial", state.onShowTutorialShell);
    GlobalEmitter.off("tutorial-finished", state.onTutorialFinishedShell);
    GlobalEmitter.off("changelog-closed", state.onChangelogClosedShell);
    GlobalEmitter.off("notifications-changed", state.updateUnreadConversationsCount);
    clearWsShellUiTimers(state);
    state.wsDisconnected = false;
    state.wsDisconnectedAt = null;
    state.wsDisconnectedDurationText = "";
    state.wsDisconnectBannerShown = false;
    state.wsReconnectedBanner = false;
    state.backendProcessExited = false;
    state.backendExitCode = null;
    state.backendRestarting = false;
    state.liveTransportReady = false;
    LiveTransport.destroy();
}

export async function bootstrapLiveTransport(state: AppShellState): Promise<void> {
    try {
        const status = await apiClient().get("/api/v1/status");
        const webtransport = status?.data?.webtransport || {};
        const mode = state.config?.live_transport_mode || "auto";
        LiveTransport.configure({ mode, webtransport });
    } catch {
        LiveTransport.configure({
            mode: state.config?.live_transport_mode || "auto",
            webtransport: { server_available: false },
        });
    }
    await LiveTransport.connect();
}

export function onLiveTransportReady(state: AppShellState): void {
    state.liveTransportReady = true;
    GlobalState.liveTransportReady = true;
    startShellPollIntervals(state);
    onWsShellReady(state);
}

export function onLiveQueueExpired(state: AppShellState): void {
    ToastUtils.warning(t("app.live_queue_expired"));
}

export function onTransportFallback(state: AppShellState): void {
    ToastUtils.warning(t("app.live_transport_fallback_websocket"));
}

export function startShellPollIntervals(state: AppShellState): void {
    clearInterval(state.reloadInterval as ReturnType<typeof setInterval>);
    clearInterval(state.appInfoInterval as ReturnType<typeof setInterval>);
    clearInterval(state.unreadCountInterval as ReturnType<typeof setInterval>);
    state.reloadInterval = null;
    state.appInfoInterval = null;
    state.unreadCountInterval = null;
    if (!state.shellRunning) {
        return;
    }
    const prefs = loadBatterySaverPrefs();
    const ready = state.liveTransportReady === true;
    const telephoneMs = ready ? 15000 : 1000;
    const unreadMs = ready ? 30000 : 5000;
    const appInfoMs = 15000;
    state.reloadInterval = setInterval(() => {
        void updateTelephoneStatus(state);
        void updatePropagationNodeStatus(state);
        state.lastAnnouncedTick += 1;
    }, applyBackgroundPollInterval(telephoneMs, prefs));
    state.appInfoInterval = setInterval(() => {
        void getAppInfo(state);
    }, applyBackgroundPollInterval(appInfoMs, prefs));
    state.unreadCountInterval = setInterval(() => {
        updateUnreadConversationsCount(state);
        updateRelayChatUnreadCount(state);
    }, applyBackgroundPollInterval(unreadMs, prefs));
}

export function onBatterySaverPrefsChangedShell(state: AppShellState): void {
    if (state.shellRunning) {
        startShellPollIntervals(state);
    }
}

export function onToastDismissedShell(state: AppShellState, payload: { key?: string }): void {
    const key = payload?.key;
    if (key === MEMORY_WARNING_TOAST_KEY) {
        markMemoryWarningDismissed();
    }
}

export function startClientHeapMemoryWatch(state: AppShellState): void {
    stopClientHeapMemoryWatch(state);
    state.clientHeapMemoryTimer = setInterval(() => {
        sampleClientHeapMemory(state);
    }, CLIENT_HEAP_SAMPLE_INTERVAL_MS);
    sampleClientHeapMemory(state);
}

export function stopClientHeapMemoryWatch(state: AppShellState): void {
    if (state.clientHeapMemoryTimer != null) {
        clearInterval(state.clientHeapMemoryTimer);
        state.clientHeapMemoryTimer = null;
    }
}

export function sampleClientHeapMemory(state: AppShellState): void {
    let memoryInfo = null;
    try {
        memoryInfo = (performance as unknown as { memory?: unknown })?.memory ?? null;
    } catch {
        memoryInfo = null;
    }
    const result = evaluateClientHeapSample(memoryInfo);
    if (result.shouldWarn) {
        showMemoryWarningToastIfNeeded(ToastUtils, { fromClientHeap: true });
    }
}

// WebSocket connection banners
// ------------------------------------------------------------------


export function init(state: AppShellState): void {
    state.disposers.push(
        watch(
            () => [
                GlobalState.authSessionResolved,
                GlobalState.authEnabled,
                GlobalState.authenticated,
                GlobalState.isLoopbackBind,
                GlobalState.demoMode,
                GlobalState.networkDegraded,
                GlobalState.networkDegradedError,
                GlobalState.networkStarting,
                GlobalState.networkReady,
                GlobalState.unreadConversationsCount,
                GlobalState.relayChatUnreadCount,
                GlobalState.missedCallsCount,
                GlobalState.activeCallTab,
                GlobalState.config?.rrc_enabled,
            ],
            () => syncGlobalMirror(state),
            { immediate: true }
        )
    );

    state.disposers.push(
        watch(
            () => fatalErrorState.active,
            (next) => {
                state.fatalError = next;
            },
            { immediate: true }
        )
    );

    state.disposers.push(
        subscribeRoute((route) => {
            const previous = state.route;
            state.route = route;
            if (previous && previous.name) {
                state.isSidebarOpen = false;
                if (state.hosts.tutorial?.isOpen?.()) {
                    state.hosts.tutorial.hide?.();
                }
            }
            applyShellAuthState(state);
            maybeNavigateNetworkRecovery(state);
        })
    );

    try {
        const savedSidebarCollapsed = loadFeatureSidebarCollapsed("app");
        if (savedSidebarCollapsed !== null) {
            state.isSidebarCollapsed = savedSidebarCollapsed;
        }
        state.sidebarNavLayoutSaved = loadAppSidebarNavLayout();
        const detailed = localStorage.getItem("meshchatx_detailed_outbound_send_status");
        if (detailed === "true" || detailed === "false") {
            GlobalState.detailedOutboundSendStatus = detailed === "true";
        }
        const grouping = localStorage.getItem("meshchatx_message_timestamp_grouping_enabled");
        if (grouping === "true" || grouping === "false") {
            GlobalState.messageTimestampGroupingEnabled = grouping === "true";
        }
        const transfer = localStorage.getItem("meshchatx_outbound_transfer_progress_enabled");
        if (transfer === "true" || transfer === "false") {
            GlobalState.outboundTransferProgressEnabled = transfer === "true";
        }
    } catch {
        // ignore
    }

    state.disposers.push(
        watch(
            () => [GlobalState.networkDegraded, GlobalState.networkDegradedError],
            () => maybeNavigateNetworkRecovery(state)
        )
    );
    maybeNavigateNetworkRecovery(state);

    const unsubscribeTheme = subscribeSystemTheme(window, (prefersDark: boolean) => {
        state.systemPrefersDark = prefersDark;
        if (state.config?.theme === "system") {
            applyAppearanceThemeFromConfig(state, state.config);
        }
    });
    if (typeof unsubscribeTheme === "function") {
        state.disposers.push(unsubscribeTheme);
    }
    applyShellAppearance(state);

    if (ElectronUtils.isElectron()) {
        const electron = electronBridge();
        if (typeof electron?.onBackendProcessExited === "function") {
            electron.onBackendProcessExited((payload: { code?: string | number }) => {
                onBackendProcessExited(state, payload);
            });
        }
        if (typeof electron?.onProtocolLink === "function") {
            electron.onProtocolLink((url: string) => {
                handleProtocolLink(router, url);
            });
        }
    }

    window.addEventListener("meshchatx-intent-uri", state.boundIntentUri);
    window.addEventListener("pointerdown", state.boundRingtoneUnlock, true);
    window.addEventListener("keydown", state.boundRingtoneUnlock, true);

    const unsubscribeOpenConversations = subscribeOpenDestinationHashes((hashes: string[]) => {
        NotificationUtils.syncAndroidNotificationContext(hashes, Boolean(state.config?.do_not_disturb_enabled));
    });
    if (typeof unsubscribeOpenConversations === "function") {
        state.disposers.push(unsubscribeOpenConversations);
    }
    NotificationUtils.syncAndroidNotificationContext(
        listOpenDestinationHashes(),
        Boolean(state.config?.do_not_disturb_enabled)
    );

    applyShellAuthState(state);
}

export function destroy(state: AppShellState): void {
    if (state.identitySaveTimer != null) {
        clearTimeout(state.identitySaveTimer);
        state.identitySaveTimer = null;
    }
    if (state.propagationSyncPollTimer != null) {
        clearInterval(state.propagationSyncPollTimer);
        state.propagationSyncPollTimer = null;
    }
    state.isPropagationSyncPolling = false;
    stopShell(state);
    clearWsShellUiTimers(state);
    if (state.endedTimeout) {
        clearTimeout(state.endedTimeout);
        state.endedTimeout = null;
    }
    stopRingtone(state);
    state.toneGenerator.stop();
    window.removeEventListener("meshchatx-intent-uri", state.boundIntentUri);
    window.removeEventListener("pointerdown", state.boundRingtoneUnlock, true);
    window.removeEventListener("keydown", state.boundRingtoneUnlock, true);
    for (const dispose of state.disposers) {
        try {
            dispose();
        } catch {
            // ignore
        }
    }
    state.disposers = [];
}
