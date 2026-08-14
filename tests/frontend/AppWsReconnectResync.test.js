// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";

vi.mock("../../meshchatx/src/frontend/js/csrfToken.js", () => ({
    fetchCsrfToken: vi.fn(async () => "refreshed"),
    getCsrfToken: vi.fn(() => "refreshed"),
    setCsrfToken: vi.fn(),
    clearCsrfToken: vi.fn(),
}));

import { fetchCsrfToken } from "../../meshchatx/src/frontend/js/csrfToken.js";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

describe("App websocket reconnect shell resync", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    function makeShellCtx(overrides = {}) {
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
            getAppInfo: vi.fn(async () => {}),
            getConfig: vi.fn(async () => {}),
            getBlockedDestinations: vi.fn(async () => {}),
            getKeyboardShortcuts: vi.fn(async () => {}),
            updateRingtonePlayer: vi.fn(async () => {}),
            updateTelephoneStatus: vi.fn(async () => {}),
            updatePropagationNodeStatus: vi.fn(async () => {}),
            resyncShellAfterWebsocketReconnect: App.methods.resyncShellAfterWebsocketReconnect,
            onWsShellConnected: App.methods.onWsShellConnected,
            onWsShellDisconnected: App.methods.onWsShellDisconnected,
            _showWsDisconnectedBannerNow: App.methods._showWsDisconnectedBannerNow,
            _tickWsDisconnectedLabel: App.methods._tickWsDisconnectedLabel,
            ...overrides,
        };
    }

    beforeEach(() => {
        window.api = {
            get: vi.fn(async (path) => {
                if (path === "/api/v1/auth/status") {
                    return { data: { auth_enabled: false, authenticated: false } };
                }
                return { data: {} };
            }),
        };
    });

    it("refreshes CSRF and shell status on reconnect after background stall recovery", async () => {
        // Oracle: forceReconnect after a backgrounded tab must still run shell
        // resync (isReconnect true) including CSRF refresh so Sync Messages POSTs work.
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const ctx = makeShellCtx();

        await App.methods.onWsShellConnected.call(ctx, { isReconnect: true });

        expect(ctx.wsDisconnected).toBe(false);
        expect(window.api.get).toHaveBeenCalledWith("/api/v1/auth/status", expect.any(Object));
        expect(fetchCsrfToken).toHaveBeenCalledTimes(1);
        expect(ctx.updatePropagationNodeStatus).toHaveBeenCalled();
        expect(ctx.getConfig).toHaveBeenCalled();
        expect(emitSpy).toHaveBeenCalledWith("websocket-reconnected");
        expect(ctx.wsReconnectedBanner).toBe(true);

        emitSpy.mockRestore();
    });

    it("resyncs silently after a brief reconnect without celebrating", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const ctx = makeShellCtx({
            wsDisconnected: false,
            wsDisconnectedAt: null,
            wsDisconnectBannerShown: false,
        });

        await App.methods.onWsShellConnected.call(ctx, { isReconnect: true });

        expect(fetchCsrfToken).toHaveBeenCalledTimes(1);
        expect(ctx.wsReconnectedBanner).toBe(false);
        expect(emitSpy).toHaveBeenCalledWith("websocket-reconnected");

        emitSpy.mockRestore();
    });

    it("does not show disconnect banner during the grace window", async () => {
        vi.useFakeTimers();
        const ctx = makeShellCtx({
            wsDisconnected: false,
            wsDisconnectedAt: null,
            wsDisconnectBannerShown: false,
            wsDisconnectGraceTimer: null,
            wsDisconnectTickTimer: null,
        });

        App.methods.onWsShellDisconnected.call(ctx);
        expect(ctx.wsDisconnected).toBe(false);
        expect(ctx.wsDisconnectGraceTimer).not.toBeNull();

        await vi.advanceTimersByTimeAsync(2499);
        expect(ctx.wsDisconnected).toBe(false);

        await vi.advanceTimersByTimeAsync(2);
        expect(ctx.wsDisconnected).toBe(true);
        expect(ctx.wsDisconnectBannerShown).toBe(true);
    });

    it("does not resync shell on the first websocket connect", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const ctx = makeShellCtx({
            wsDisconnected: false,
            wsDisconnectedAt: null,
            wsDisconnectBannerShown: false,
        });

        await App.methods.onWsShellConnected.call(ctx, { isReconnect: false });

        expect(fetchCsrfToken).not.toHaveBeenCalled();
        expect(ctx.updatePropagationNodeStatus).not.toHaveBeenCalled();
        expect(emitSpy).not.toHaveBeenCalledWith("websocket-reconnected");

        emitSpy.mockRestore();
    });
});
