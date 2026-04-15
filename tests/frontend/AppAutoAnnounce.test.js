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
    },
}));

describe("App.vue sidebar announce and auto-announce interval", () => {
    const axiosMock = { get: vi.fn() };

    beforeEach(() => {
        vi.clearAllMocks();
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

    it("onAnnounceIntervalSecondsChange sends config.set with interval", async () => {
        const ctx = {
            config: { auto_announce_interval_seconds: 3600 },
            updateConfig: App.methods.updateConfig,
            $t: (k) => k,
        };

        await App.methods.onAnnounceIntervalSecondsChange.call(ctx);

        expect(WebSocketConnection.send).toHaveBeenCalled();
        const raw = WebSocketConnection.send.mock.calls[0][0];
        const parsed = JSON.parse(raw);
        expect(parsed.type).toBe("config.set");
        expect(parsed.config.auto_announce_interval_seconds).toBe(3600);
    });
});
