// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import { useWsDisconnectBanner } from "../../meshchatx/src/frontend/js/app/useWsDisconnectBanner.js";
import { WS_DISCONNECT_BANNER_GRACE_MS } from "../../meshchatx/src/frontend/js/wsConnectionSupport";

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

    function makeResyncCtx(overrides = {}) {
        return {
            shellRunning: true,
            liveTransportReady: false,
            getAppInfo: vi.fn(async () => {}),
            getConfig: vi.fn(async () => {}),
            getBlockedDestinations: vi.fn(async () => {}),
            getKeyboardShortcuts: vi.fn(async () => {}),
            updateRingtonePlayer: vi.fn(async () => {}),
            updateTelephoneStatus: vi.fn(async () => {}),
            updatePropagationNodeStatus: vi.fn(async () => {}),
            ...overrides,
        };
    }

    function makeBanner({ resyncCtx, isShellRunning = true } = {}) {
        const ctx = resyncCtx || makeResyncCtx();
        const banner = useWsDisconnectBanner({
            isShellRunning: () => isShellRunning,
            onTransportDown: vi.fn(),
            onReconnect: () => App.methods.resyncShellAfterWebsocketReconnect.call(ctx),
        });
        return { banner, ctx };
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
        const { banner, ctx } = makeBanner();
        banner.wsDisconnected.value = true;
        banner.wsDisconnectedAt.value = Date.now() - 5000;
        banner.wsDisconnectedDurationText.value = "5s";
        banner.wsDisconnectBannerShown.value = true;

        await banner.onWsShellConnected({ isReconnect: true });

        expect(banner.wsDisconnected.value).toBe(true);
        expect(window.api.get).toHaveBeenCalledWith("/api/v1/auth/status", expect.any(Object));
        expect(fetchCsrfToken).toHaveBeenCalledTimes(1);
        expect(ctx.updatePropagationNodeStatus).toHaveBeenCalled();
        expect(ctx.getConfig).toHaveBeenCalled();
        expect(emitSpy).toHaveBeenCalledWith("websocket-reconnected");
        expect(banner.wsReconnectedBanner.value).toBe(false);

        banner.onWsShellReady();

        expect(banner.wsDisconnected.value).toBe(false);
        expect(banner.wsReconnectedBanner.value).toBe(true);

        emitSpy.mockRestore();
    });

    it("resyncs silently after a brief reconnect without celebrating", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const { banner } = makeBanner();

        await banner.onWsShellConnected({ isReconnect: true });

        expect(fetchCsrfToken).toHaveBeenCalledTimes(1);
        expect(banner.wsReconnectedBanner.value).toBe(false);
        expect(emitSpy).toHaveBeenCalledWith("websocket-reconnected");

        banner.onWsShellReady();
        expect(banner.wsReconnectedBanner.value).toBe(false);

        emitSpy.mockRestore();
    });

    it("does not show disconnect banner during the grace window", async () => {
        vi.useFakeTimers();
        const { banner } = makeBanner();

        banner.onWsShellDisconnected();
        expect(banner.wsDisconnected.value).toBe(false);

        await vi.advanceTimersByTimeAsync(WS_DISCONNECT_BANNER_GRACE_MS - 1);
        expect(banner.wsDisconnected.value).toBe(false);

        await vi.advanceTimersByTimeAsync(2);
        expect(banner.wsDisconnected.value).toBe(true);
        expect(banner.wsDisconnectBannerShown.value).toBe(true);
    });

    it("keeps disconnect grace across a TCP open that never becomes ready", async () => {
        vi.useFakeTimers();
        const { banner } = makeBanner();

        banner.onWsShellDisconnected();
        await vi.advanceTimersByTimeAsync(1000);

        await banner.onWsShellConnected({ isReconnect: true });
        expect(banner.wsDisconnected.value).toBe(false);

        banner.onWsShellDisconnected();
        await vi.advanceTimersByTimeAsync(WS_DISCONNECT_BANNER_GRACE_MS - 1000);
        expect(banner.wsDisconnected.value).toBe(true);
        expect(banner.wsDisconnectBannerShown.value).toBe(true);
    });

    it("does not resync shell on the first websocket connect", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const resyncCtx = makeResyncCtx();
        const { banner } = makeBanner({ resyncCtx });

        await banner.onWsShellConnected({ isReconnect: false });

        expect(fetchCsrfToken).not.toHaveBeenCalled();
        expect(resyncCtx.updatePropagationNodeStatus).not.toHaveBeenCalled();
        expect(emitSpy).not.toHaveBeenCalledWith("websocket-reconnected");

        banner.onWsShellReady();
        expect(banner.wsReconnectedBanner.value).toBe(false);

        emitSpy.mockRestore();
    });
});
