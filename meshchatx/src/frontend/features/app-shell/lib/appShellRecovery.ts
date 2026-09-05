// SPDX-License-Identifier: 0BSD

/**
 * Backend offline banners, WebSocket disconnect UI, and the recovery actions
 * behind them: restart, database auto-recover, network recover, crash report.
 */

import DialogUtils from "../../../js/DialogUtils.js";
import { formatDisconnectedDuration, WS_DISCONNECT_BANNER_GRACE_MS } from "../../../js/wsConnectionSupport.js";
import { applyAuthStatusToGlobalState, fetchAuthStatus } from "../../../js/authSessionSync.js";
import GlobalState, { mergeGlobalConfig } from "../../../js/GlobalState.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import {
    shouldShowLanBindNoAuthBanner,
    dismissLanBindNoAuthBanner,
    isLanBindNoAuthBannerDismissed,
} from "../../../js/lanBindWarning.js";
import { fetchCsrfToken } from "../../../js/csrfToken.js";
import { onWsEvent, offWsEvent } from "../../../js/registries/wsEventRegistry.js";
import { isDatabaseRecoveryError, recoveryLocationForNetworkError } from "../../../js/networkRecovery.js";
import { navigate, router, subscribe as subscribeRoute } from "../../../shell/hashRouter.js";
import { createShellWsHandlers } from "./appShellWsHandlers.js";
import { apiClient, electronBridge } from "./appShellShared.js";
import { startShellPollIntervals } from "./appShellLifecycle.js";
import { getAppInfo, getBlockedDestinations, getConfig, getKeyboardShortcuts } from "./appShellConfig.js";
import { updatePropagationNodeStatus } from "./appShellPropagation.js";
import { updateRingtonePlayer, updateTelephoneStatus } from "./appShellTelephony.js";
import type { AppShellState } from "./appShellState.svelte.js";

export function onBackendProcessExited(state: AppShellState, payload: { code?: string | number } = {}): void {
    if (!state.shellRunning) {
        return;
    }
    state.backendProcessExited = true;
    state.backendExitCode = payload?.code ?? null;
    // Process exit is serious: show disconnect immediately.
    showWsDisconnectedBannerNow(state);
}

export function showWsDisconnectedBannerNow(state: AppShellState): void {
    if (!state.shellRunning) {
        return;
    }
    if (state.wsDisconnectGraceTimer != null) {
        clearTimeout(state.wsDisconnectGraceTimer);
        state.wsDisconnectGraceTimer = null;
    }
    state.wsDisconnected = true;
    state.wsDisconnectBannerShown = true;
    state.wsDisconnectedAt = state.wsDisconnectedAt || Date.now();
    tickWsDisconnectedLabel(state);
    if (state.wsDisconnectTickTimer != null) {
        clearInterval(state.wsDisconnectTickTimer);
    }
    state.wsDisconnectTickTimer = setInterval(() => tickWsDisconnectedLabel(state), 1000);
}

export function onWsShellDisconnected(state: AppShellState): void {
    if (!state.shellRunning) {
        return;
    }
    state.liveTransportReady = false;
    GlobalState.liveTransportReady = false;
    startShellPollIntervals(state);
    // Ignore brief reconnect blips (startup, Android resume). Only scare
    // the user if the socket stays down past the grace window.
    if (state.wsDisconnected) {
        return;
    }
    if (state.wsDisconnectGraceTimer != null) {
        return;
    }
    state.wsDisconnectedAt = Date.now();
    state.wsDisconnectGraceTimer = setTimeout(() => {
        state.wsDisconnectGraceTimer = null;
        showWsDisconnectedBannerNow(state);
    }, WS_DISCONNECT_BANNER_GRACE_MS);
}

export function tickWsDisconnectedLabel(state: AppShellState): void {
    if (!state.wsDisconnectedAt) {
        state.wsDisconnectedDurationText = "";
        return;
    }
    state.wsDisconnectedDurationText = formatDisconnectedDuration(Date.now() - state.wsDisconnectedAt);
}

export function clearWsDisconnectedUi(state: AppShellState): void {
    if (state.wsDisconnectGraceTimer != null) {
        clearTimeout(state.wsDisconnectGraceTimer);
        state.wsDisconnectGraceTimer = null;
    }
    state.wsDisconnected = false;
    state.wsDisconnectedAt = null;
    state.wsDisconnectedDurationText = "";
    state.wsDisconnectBannerShown = false;
    state.backendProcessExited = false;
    state.backendExitCode = null;
    if (state.wsDisconnectTickTimer != null) {
        clearInterval(state.wsDisconnectTickTimer);
        state.wsDisconnectTickTimer = null;
    }
}

export function celebrateWsReconnected(state: AppShellState): void {
    state.wsReconnectedBanner = true;
    if (state.wsReconnectedHideTimer != null) {
        clearTimeout(state.wsReconnectedHideTimer);
    }
    state.wsReconnectedHideTimer = setTimeout(() => {
        state.wsReconnectedBanner = false;
        state.wsReconnectedHideTimer = null;
    }, 4500);
}

export async function onWsShellConnected(state: AppShellState, payload: { isReconnect?: boolean } = {}): Promise<void> {
    if (!state.shellRunning) {
        return;
    }
    // TCP open is not recovery. Vite proxies and restart flaps can OPEN then
    // CLOSE without a backend frame. Keep the grace timer running until ready.
    if (payload.isReconnect === true) {
        await resyncShellAfterWebsocketReconnect(state);
    }
}

export function onWsShellReady(state: AppShellState): void {
    if (!state.shellRunning) {
        return;
    }
    const sawDisconnectBanner = state.wsDisconnectBannerShown;
    clearWsDisconnectedUi(state);
    if (sawDisconnectBanner) {
        celebrateWsReconnected(state);
    }
}

export async function resyncShellAfterWebsocketReconnect(state: AppShellState): Promise<void> {
    try {
        const status = await fetchAuthStatus(apiClient());
        applyAuthStatusToGlobalState(status);
    } catch {
        // ignore
    }
    try {
        await fetchCsrfToken(apiClient());
    } catch {
        // ignore
    }
    for (const step of [
        () => getAppInfo(state),
        () => getConfig(state),
        () => getBlockedDestinations(state),
        () => getKeyboardShortcuts(state),
        () => updateRingtonePlayer(state),
        () => updateTelephoneStatus(state),
        () => updatePropagationNodeStatus(state),
    ]) {
        try {
            await step();
        } catch {
            // ignore
        }
    }
    GlobalEmitter.emit("websocket-reconnected");
}

// Banner actions
// ------------------------------------------------------------------
export async function onRestartBackend(state: AppShellState): Promise<void> {
    const electron = electronBridge();
    if (!electron?.restartBackend) {
        return;
    }
    state.backendRestarting = true;
    try {
        const result = await electron.restartBackend();
        if (!result?.ok) {
            ToastUtils.error(result?.error || t("app.restart_backend_failed"));
            return;
        }
        ToastUtils.info(t("app.restart_backend_started"));
    } catch {
        ToastUtils.error(t("app.restart_backend_failed"));
    } finally {
        state.backendRestarting = false;
    }
}

export async function onViewBackendCrashReport(state: AppShellState): Promise<void> {
    const electron = electronBridge();
    if (!electron?.openBackendCrashReport) {
        return;
    }
    try {
        const result = await electron.openBackendCrashReport();
        if (!result?.ok) {
            ToastUtils.error(result?.error || t("app.view_backend_logs_failed"));
        }
    } catch {
        ToastUtils.error(t("app.view_backend_logs_failed"));
    }
}

export function onOpenInterfacesForRecovery(state: AppShellState): void {
    void navigate({ name: "interfaces" });
}

export function onOpenSettingsForRecovery(state: AppShellState): void {
    void navigate({ name: "settings" });
}

export function onDismissLanBindNoAuthBanner(state: AppShellState): void {
    dismissLanBindNoAuthBanner();
    state.lanBindNoAuthBannerDismissed = true;
}

export function onOpenBackupsForRecovery(state: AppShellState): void {
    void navigate({ name: "about", hash: "#about-database-backups" });
}

export async function onAutoRecoverDatabase(state: AppShellState): Promise<void> {
    if (state.databaseAutoRecovering) {
        return;
    }
    if (!(await DialogUtils.confirm(t("about.auto_recover_confirm")))) {
        return;
    }
    state.databaseAutoRecovering = true;
    try {
        const response = await apiClient().post("/api/v1/database/auto-recover", { relaunch: true });
        const strategy = response.data?.strategy;
        const message = response.data?.message;
        if (strategy === "restore_backup") {
            ToastUtils.success(message || t("about.auto_recover_backup"));
            if (response.data?.requires_relaunch) {
                return;
            }
        } else if (strategy === "sqlite_recovery") {
            ToastUtils.success(message || t("about.recovery_complete"));
            await onRecoverNetwork(state);
        } else {
            ToastUtils.error(message || t("about.auto_recover_failed"));
        }
    } catch (e) {
        const error = e as { response?: { data?: { message?: string; error?: string } } };
        ToastUtils.error(
            error.response?.data?.message || error.response?.data?.error || t("about.auto_recover_failed")
        );
    } finally {
        state.databaseAutoRecovering = false;
    }
}

export async function onRecoverNetwork(state: AppShellState): Promise<void> {
    if (state.networkRecovering) {
        return;
    }
    state.networkRecovering = true;
    try {
        const response = await apiClient().post("/api/v1/reticulum/recover", {});
        if (response.data?.status?.network_ready) {
            GlobalState.networkDegraded = false;
            GlobalState.networkDegradedError = null;
            ToastUtils.success(response.data.message || t("app.network_recovered"));
            return;
        }
        const error = response.data?.error || response.data?.message || t("app.network_recover_failed");
        GlobalState.networkDegradedError = error;
        ToastUtils.error(error);
    } catch (e) {
        const failure = e as { response?: { data?: { message?: string; error?: string } } };
        const error =
            failure.response?.data?.error || failure.response?.data?.message || t("app.network_recover_failed");
        GlobalState.networkDegradedError = error;
        ToastUtils.error(error);
    } finally {
        state.networkRecovering = false;
    }
}

export function maybeNavigateNetworkRecovery(state: AppShellState): void {
    if (!GlobalState.networkDegraded || state.isAuthRoute) {
        return;
    }
    const location = recoveryLocationForNetworkError(GlobalState.networkDegradedError);
    if (!location) {
        return;
    }
    if (location.name === "about" && state.routeName === "about" && state.route?.hash === "#about-database-backups") {
        return;
    }
    void navigate(location);
}

export function registerShellWsHandlers(state: AppShellState): void {
    unregisterShellWsHandlers(state);
    const handlers = createShellWsHandlers(state);
    for (const [type, handler] of Object.entries(handlers)) {
        const bound = (payload: any) => handler(payload);
        onWsEvent(type, bound);
        state.shellWsHandlerCleanups.push(() => offWsEvent(type, bound));
    }
}

export function unregisterShellWsHandlers(state: AppShellState): void {
    for (const cleanup of state.shellWsHandlerCleanups) {
        cleanup();
    }
    state.shellWsHandlerCleanups = [];
}

export function clearWsShellUiTimers(state: AppShellState): void {
    if (state.wsDisconnectTickTimer != null) {
        clearInterval(state.wsDisconnectTickTimer);
        state.wsDisconnectTickTimer = null;
    }
    if (state.wsDisconnectGraceTimer != null) {
        clearTimeout(state.wsDisconnectGraceTimer);
        state.wsDisconnectGraceTimer = null;
    }
    if (state.wsReconnectedHideTimer != null) {
        clearTimeout(state.wsReconnectedHideTimer);
        state.wsReconnectedHideTimer = null;
    }
}
