import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(),
        connect: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
        destroy: vi.fn(),
        setLiveSendBridge: vi.fn(),
        isOpen: vi.fn(() => false),
        reconnect: vi.fn(),
    },
}));

describe("App.vue sidebar announce and auto-announce interval", () => {
    const axiosMock = { get: vi.fn(), patch: vi.fn() };

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock.patch.mockResolvedValue({
            data: { config: { auto_announce_interval_seconds: 3600 } },
        });
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
    });

    it("sendAnnounce requests announce endpoint and refreshes config", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/announce") {
                return Promise.resolve({ data: {} });
            }
            if (url === "/api/v1/config") {
                return Promise.resolve({
                    data: {
                        config: {
                            last_announced_at: Math.floor(Date.now() / 1000),
                            auto_announce_interval_seconds: 3600,
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const ctx = {
            config: { auto_announce_interval_seconds: 3600 },
            getConfig: App.methods.getConfig,
            $t: (k) => k,
        };

        await App.methods.sendAnnounce.call(ctx);

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announce");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
        expect(ToastUtils.success).toHaveBeenCalled();
        expect(ctx.config.last_announced_at).toBeDefined();
    });

    it("sendAnnounce surfaces failure toast on announce error", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/announce") {
                return Promise.reject(new Error("network"));
            }
            return Promise.resolve({ data: {} });
        });

        const ctx = {
            config: {},
            getConfig: vi.fn(),
            $t: (k) => k,
        };

        await App.methods.sendAnnounce.call(ctx);

        expect(ToastUtils.error).toHaveBeenCalled();
    });

    it("onAnnounceIntervalSecondsChange PATCHes announce interval", async () => {
        const ctx = {
            config: { auto_announce_interval_seconds: 3600 },
            updateConfig: App.methods.updateConfig,
            $t: (k) => k,
        };

        await App.methods.onAnnounceIntervalSecondsChange.call(ctx);

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/config", {
            auto_announce_interval_seconds: 3600,
        });
    });

    it("applyAnnouncedEvent writes last_announced_at without waiting for config GET", () => {
        const ctx = {
            config: { identity_hash: "h1", last_announced_at: 100 },
            getConfig: vi.fn(),
        };

        App.methods.applyAnnouncedEvent.call(ctx, {
            type: "announced",
            identity_hash: "h1",
            last_announced_at: 1_700_000_000,
        });

        expect(ctx.config.last_announced_at).toBe(1_700_000_000);
        expect(ctx.getConfig).not.toHaveBeenCalled();
    });

    it("applyAnnouncedEvent ignores a stamp from another identity", () => {
        const ctx = {
            config: { identity_hash: "h1", last_announced_at: 100 },
            getConfig: vi.fn(),
        };

        App.methods.applyAnnouncedEvent.call(ctx, {
            type: "announced",
            identity_hash: "h2",
            last_announced_at: 1_700_000_000,
        });

        expect(ctx.config.last_announced_at).toBe(100);
        expect(ctx.getConfig).not.toHaveBeenCalled();
    });

    it("applyAnnouncedEvent falls back to getConfig when stamp is missing", () => {
        const ctx = {
            config: { identity_hash: "h1", last_announced_at: 100 },
            getConfig: vi.fn(),
        };

        App.methods.applyAnnouncedEvent.call(ctx, {
            type: "announced",
            identity_hash: "h1",
        });

        expect(ctx.config.last_announced_at).toBe(100);
        expect(ctx.getConfig).toHaveBeenCalledTimes(1);
    });
});
