// @ts-check

import { ref } from "vue";

import { formatDisconnectedDuration, WS_DISCONNECT_BANNER_GRACE_MS } from "../wsConnectionSupport.js";

/**
 * Websocket disconnect and backend-exit banner state for the app shell.
 *
 * options.isShellRunning gates every entry point. options.onTransportDown
 * runs on disconnect (the host mirrors liveTransportReady and restarts
 * shell poll intervals). options.onReconnect runs when a reconnect event
 * reports isReconnect true (the host resyncs auth, CSRF, and shell data).
 */
export function useWsDisconnectBanner(options = {}) {
    const { isShellRunning, onTransportDown, onReconnect } = options;

    const wsDisconnected = ref(false);
    const wsDisconnectedAt = ref(null);
    const wsDisconnectedDurationText = ref("");
    const wsReconnectedBanner = ref(false);
    const wsDisconnectBannerShown = ref(false);
    const backendProcessExited = ref(false);
    const backendExitCode = ref(null);

    let wsDisconnectTickTimer = null;
    let wsDisconnectGraceTimer = null;
    let wsReconnectedHideTimer = null;

    function _tickWsDisconnectedLabel() {
        if (!wsDisconnectedAt.value) {
            wsDisconnectedDurationText.value = "";
            return;
        }
        wsDisconnectedDurationText.value = formatDisconnectedDuration(Date.now() - wsDisconnectedAt.value);
    }

    function _showWsDisconnectedBannerNow() {
        if (!isShellRunning?.()) {
            return;
        }
        if (wsDisconnectGraceTimer != null) {
            clearTimeout(wsDisconnectGraceTimer);
            wsDisconnectGraceTimer = null;
        }
        wsDisconnected.value = true;
        wsDisconnectBannerShown.value = true;
        wsDisconnectedAt.value = wsDisconnectedAt.value || Date.now();
        _tickWsDisconnectedLabel();
        if (wsDisconnectTickTimer != null) {
            clearInterval(wsDisconnectTickTimer);
        }
        wsDisconnectTickTimer = setInterval(() => _tickWsDisconnectedLabel(), 1000);
    }

    function onWsShellDisconnected() {
        if (!isShellRunning?.()) {
            return;
        }
        onTransportDown?.();
        // Ignore brief reconnect blips (startup, Android resume). Only scare
        // the user if the socket stays down past the grace window.
        if (wsDisconnected.value) {
            return;
        }
        if (wsDisconnectGraceTimer != null) {
            return;
        }
        wsDisconnectedAt.value = Date.now();
        wsDisconnectGraceTimer = setTimeout(() => {
            wsDisconnectGraceTimer = null;
            _showWsDisconnectedBannerNow();
        }, WS_DISCONNECT_BANNER_GRACE_MS);
    }

    function _clearWsDisconnectedUi() {
        if (wsDisconnectGraceTimer != null) {
            clearTimeout(wsDisconnectGraceTimer);
            wsDisconnectGraceTimer = null;
        }
        wsDisconnected.value = false;
        wsDisconnectedAt.value = null;
        wsDisconnectedDurationText.value = "";
        wsDisconnectBannerShown.value = false;
        backendProcessExited.value = false;
        backendExitCode.value = null;
        if (wsDisconnectTickTimer != null) {
            clearInterval(wsDisconnectTickTimer);
            wsDisconnectTickTimer = null;
        }
    }

    function _celebrateWsReconnected() {
        wsReconnectedBanner.value = true;
        if (wsReconnectedHideTimer != null) {
            clearTimeout(wsReconnectedHideTimer);
        }
        wsReconnectedHideTimer = setTimeout(() => {
            wsReconnectedBanner.value = false;
            wsReconnectedHideTimer = null;
        }, 4500);
    }

    async function onWsShellConnected(payload = {}) {
        if (!isShellRunning?.()) {
            return;
        }
        // TCP open is not recovery. Vite proxies and restart flaps can OPEN then
        // CLOSE without a backend frame. Keep the grace timer running until ready.
        const isReconnect = payload.isReconnect === true;
        if (isReconnect) {
            await onReconnect?.();
        }
    }

    function onWsShellReady() {
        if (!isShellRunning?.()) {
            return;
        }
        const sawDisconnectBanner = wsDisconnectBannerShown.value;
        _clearWsDisconnectedUi();
        if (sawDisconnectBanner) {
            _celebrateWsReconnected();
        }
    }

    function onBackendProcessExited(payload = {}) {
        if (!isShellRunning?.()) {
            return;
        }
        backendProcessExited.value = true;
        backendExitCode.value = payload?.code ?? null;
        // Process exit is serious: show disconnect immediately.
        _showWsDisconnectedBannerNow();
    }

    function clearWsShellUiTimers() {
        if (wsDisconnectTickTimer != null) {
            clearInterval(wsDisconnectTickTimer);
            wsDisconnectTickTimer = null;
        }
        if (wsDisconnectGraceTimer != null) {
            clearTimeout(wsDisconnectGraceTimer);
            wsDisconnectGraceTimer = null;
        }
        if (wsReconnectedHideTimer != null) {
            clearTimeout(wsReconnectedHideTimer);
            wsReconnectedHideTimer = null;
        }
    }

    function resetWsDisconnectBanner() {
        clearWsShellUiTimers();
        _clearWsDisconnectedUi();
        wsReconnectedBanner.value = false;
    }

    return {
        wsDisconnected,
        wsDisconnectedAt,
        wsDisconnectedDurationText,
        wsReconnectedBanner,
        wsDisconnectBannerShown,
        backendProcessExited,
        backendExitCode,
        onWsShellDisconnected,
        onWsShellConnected,
        onWsShellReady,
        onBackendProcessExited,
        clearWsShellUiTimers,
        resetWsDisconnectBanner,
        _showWsDisconnectedBannerNow,
        _tickWsDisconnectedLabel,
        _clearWsDisconnectedUi,
        _celebrateWsReconnected,
    };
}
