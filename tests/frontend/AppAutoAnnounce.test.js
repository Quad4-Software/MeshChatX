import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    sendAnnounce,
    onAnnounceIntervalChange,
} from "../../meshchatx/src/frontend/features/app-shell/lib/appShellIdentity.js";
import { applyAnnouncedEvent } from "../../meshchatx/src/frontend/features/app-shell/lib/appShellConfig.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.js";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe("app-shell sidebar announce and auto-announce interval", () => {
    const axiosMock = { get: vi.fn(), patch: vi.fn(), post: vi.fn() };

    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            app: {
                announce_sent: "announced",
                failed_announce: "failed",
            },
            common: {
                saved_setting: "saved {label}",
                failed_save_setting: "failed {label}",
            },
        });
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

        const state = {
            config: { auto_announce_interval_seconds: 3600 },
        };

        await sendAnnounce(state);

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announce");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
        expect(ToastUtils.success).toHaveBeenCalled();
        expect(state.config.last_announced_at).toBeDefined();
    });

    it("sendAnnounce surfaces failure toast on announce error", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/announce") {
                return Promise.reject(new Error("network"));
            }
            if (url === "/api/v1/config") {
                return Promise.resolve({ data: { config: {} } });
            }
            return Promise.resolve({ data: {} });
        });

        const state = { config: {} };
        await sendAnnounce(state);

        expect(ToastUtils.error).toHaveBeenCalled();
    });

    it("onAnnounceIntervalChange PATCHes announce interval", async () => {
        const state = {
            config: { auto_announce_interval_seconds: 1800 },
        };

        await onAnnounceIntervalChange(state, 3600);

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/config", {
            auto_announce_interval_seconds: 3600,
        });
        expect(state.config.auto_announce_interval_seconds).toBe(3600);
    });

    it("applyAnnouncedEvent writes last_announced_at without waiting for config GET", () => {
        const state = {
            config: { identity_hash: "h1", last_announced_at: 100 },
        };

        applyAnnouncedEvent(state, {
            type: "announced",
            identity_hash: "h1",
            last_announced_at: 1_700_000_000,
        });

        expect(state.config.last_announced_at).toBe(1_700_000_000);
        expect(axiosMock.get).not.toHaveBeenCalled();
    });

    it("applyAnnouncedEvent ignores a stamp from another identity", () => {
        const state = {
            config: { identity_hash: "h1", last_announced_at: 100 },
        };

        applyAnnouncedEvent(state, {
            type: "announced",
            identity_hash: "h2",
            last_announced_at: 1_700_000_000,
        });

        expect(state.config.last_announced_at).toBe(100);
        expect(axiosMock.get).not.toHaveBeenCalled();
    });

    it("applyAnnouncedEvent falls back to getConfig when stamp is missing", async () => {
        axiosMock.get.mockResolvedValue({
            data: { config: { identity_hash: "h1", last_announced_at: 100 } },
        });
        const state = {
            config: { identity_hash: "h1", last_announced_at: 100 },
        };

        applyAnnouncedEvent(state, {
            type: "announced",
            identity_hash: "h1",
        });

        await Promise.resolve();
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
    });
});
