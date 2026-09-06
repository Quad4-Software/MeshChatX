// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WS_DISCONNECT_BANNER_GRACE_MS } from "../../meshchatx/src/frontend/js/wsConnectionSupport";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

const getAppInfo = vi.fn(async () => {});
const getConfig = vi.fn(async () => {});
const getBlockedDestinations = vi.fn(async () => {});
const getKeyboardShortcuts = vi.fn(async () => {});
const updateRingtonePlayer = vi.fn(async () => {});
const updateTelephoneStatus = vi.fn(async () => {});
const updatePropagationNodeStatus = vi.fn(async () => {});
const startShellPollIntervals = vi.fn();

vi.mock("../../meshchatx/src/frontend/js/csrfToken.js", () => ({
    fetchCsrfToken: vi.fn(async () => "refreshed"),
    getCsrfToken: vi.fn(() => "refreshed"),
    setCsrfToken: vi.fn(),
    clearCsrfToken: vi.fn(),
}));

vi.mock("../../meshchatx/src/frontend/features/app-shell/lib/appShellConfig.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getAppInfo: (...a) => getAppInfo(...a),
        getConfig: (...a) => getConfig(...a),
        getBlockedDestinations: (...a) => getBlockedDestinations(...a),
        getKeyboardShortcuts: (...a) => getKeyboardShortcuts(...a),
    };
});

vi.mock("../../meshchatx/src/frontend/features/app-shell/lib/appShellTelephony.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        updateRingtonePlayer: (...a) => updateRingtonePlayer(...a),
        updateTelephoneStatus: (...a) => updateTelephoneStatus(...a),
    };
});

vi.mock("../../meshchatx/src/frontend/features/app-shell/lib/appShellPropagation.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        updatePropagationNodeStatus: (...a) => updatePropagationNodeStatus(...a),
    };
});

vi.mock("../../meshchatx/src/frontend/features/app-shell/lib/appShellLifecycle.js", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        startShellPollIntervals: (...a) => startShellPollIntervals(...a),
    };
});

import { fetchCsrfToken } from "../../meshchatx/src/frontend/js/csrfToken.js";
import {
    onWsShellConnected,
    onWsShellDisconnected,
    onWsShellReady,
} from "../../meshchatx/src/frontend/features/app-shell/lib/appShellRecovery.js";

describe("App websocket reconnect shell resync", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.api = {
            get: vi.fn(async (path) => {
                if (path === "/api/v1/auth/status") {
                    return { data: { auth_enabled: false, authenticated: false } };
                }
                return { data: {} };
            }),
        };
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    function makeState(overrides = {}) {
        return {
            shellRunning: true,
            wsDisconnected: true,
            wsDisconnectedAt: Date.now() - 5000,
            wsDisconnectedDurationText: "5s",
            wsDisconnectBannerShown: true,
            wsDisconnectGraceTimer: null,
            backendProcessExited: false,
            backendExitCode: null,
            wsDisconnectTickTimer: null,
            wsReconnectedBanner: false,
            wsReconnectedHideTimer: null,
            liveTransportReady: false,
            ...overrides,
        };
    }

    it("refreshes CSRF and shell status on reconnect after background stall recovery", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const state = makeState();

        await onWsShellConnected(state, { isReconnect: true });

        expect(state.wsDisconnected).toBe(true);
        expect(window.api.get).toHaveBeenCalledWith("/api/v1/auth/status", expect.any(Object));
        expect(fetchCsrfToken).toHaveBeenCalledTimes(1);
        expect(updatePropagationNodeStatus).toHaveBeenCalled();
        expect(getConfig).toHaveBeenCalled();
        expect(emitSpy).toHaveBeenCalledWith("websocket-reconnected");
        expect(state.wsReconnectedBanner).toBe(false);

        onWsShellReady(state);

        expect(state.wsDisconnected).toBe(false);
        expect(state.wsReconnectedBanner).toBe(true);

        emitSpy.mockRestore();
    });

    it("resyncs silently after a brief reconnect without celebrating", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const state = makeState({
            wsDisconnected: false,
            wsDisconnectedAt: null,
            wsDisconnectBannerShown: false,
        });

        await onWsShellConnected(state, { isReconnect: true });

        expect(fetchCsrfToken).toHaveBeenCalledTimes(1);
        expect(state.wsReconnectedBanner).toBe(false);
        expect(emitSpy).toHaveBeenCalledWith("websocket-reconnected");

        onWsShellReady(state);
        expect(state.wsReconnectedBanner).toBe(false);

        emitSpy.mockRestore();
    });

    it("does not show disconnect banner during the grace window", async () => {
        vi.useFakeTimers();
        const state = makeState({
            wsDisconnected: false,
            wsDisconnectedAt: null,
            wsDisconnectBannerShown: false,
            wsDisconnectGraceTimer: null,
            wsDisconnectTickTimer: null,
        });

        onWsShellDisconnected(state);
        expect(state.wsDisconnected).toBe(false);
        expect(state.wsDisconnectGraceTimer).not.toBeNull();

        await vi.advanceTimersByTimeAsync(WS_DISCONNECT_BANNER_GRACE_MS - 1);
        expect(state.wsDisconnected).toBe(false);

        await vi.advanceTimersByTimeAsync(2);
        expect(state.wsDisconnected).toBe(true);
        expect(state.wsDisconnectBannerShown).toBe(true);
    });

    it("keeps disconnect grace across a TCP open that never becomes ready", async () => {
        vi.useFakeTimers();
        const state = makeState({
            wsDisconnected: false,
            wsDisconnectedAt: null,
            wsDisconnectBannerShown: false,
            wsDisconnectGraceTimer: null,
            wsDisconnectTickTimer: null,
        });

        onWsShellDisconnected(state);
        await vi.advanceTimersByTimeAsync(1000);

        await onWsShellConnected(state, { isReconnect: true });
        expect(state.wsDisconnected).toBe(false);
        expect(state.wsDisconnectGraceTimer).not.toBeNull();

        onWsShellDisconnected(state);
        await vi.advanceTimersByTimeAsync(WS_DISCONNECT_BANNER_GRACE_MS - 1000);
        expect(state.wsDisconnected).toBe(true);
        expect(state.wsDisconnectBannerShown).toBe(true);
    });

    it("does not resync shell on the first websocket connect", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const state = makeState({
            wsDisconnected: false,
            wsDisconnectedAt: null,
            wsDisconnectBannerShown: false,
        });

        await onWsShellConnected(state, { isReconnect: false });

        expect(fetchCsrfToken).not.toHaveBeenCalled();
        expect(updatePropagationNodeStatus).not.toHaveBeenCalled();
        expect(emitSpy).not.toHaveBeenCalledWith("websocket-reconnected");

        onWsShellReady(state);
        expect(state.wsReconnectedBanner).toBe(false);

        emitSpy.mockRestore();
    });
});
