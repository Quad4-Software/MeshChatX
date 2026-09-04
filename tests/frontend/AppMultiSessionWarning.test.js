// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

function makeContext(overrides = {}) {
    return {
        config: { multi_session_warning_enabled: true },
        multiSessionWarningActive: false,
        handleActiveSessionsUpdated: App.methods.handleActiveSessionsUpdated,
        $t(key, params = {}) {
            if (key === "app.multi_session_warning") {
                return `multi ${params.count}`;
            }
            return key;
        },
        ...overrides,
    };
}

describe("App multi-session warning toast", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("toasts when two sessions connect and setting is enabled", () => {
        const ctx = makeContext();
        ctx.handleActiveSessionsUpdated({
            count: 2,
            warning_enabled: true,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }],
        });
        expect(ToastUtils.warning).toHaveBeenCalledWith("multi 2");
        expect(ctx.multiSessionWarningActive).toBe(true);
    });

    it("does not toast for localhost or lan-only sessions", () => {
        const ctx = makeContext();
        ctx.handleActiveSessionsUpdated({
            count: 2,
            warning_enabled: true,
            sessions: [{ ip: "127.0.0.1" }, { ip: "192.168.1.10" }],
        });
        expect(ToastUtils.warning).not.toHaveBeenCalled();
        expect(ctx.multiSessionWarningActive).toBe(false);
    });

    it("does not toast again while still above the threshold", () => {
        const ctx = makeContext({ multiSessionWarningActive: true });
        ctx.handleActiveSessionsUpdated({
            count: 3,
            warning_enabled: true,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }, { ip: "3.3.3.3" }],
        });
        expect(ToastUtils.warning).not.toHaveBeenCalled();
        expect(ctx.multiSessionWarningActive).toBe(true);
    });

    it("does not toast when the setting is disabled", () => {
        const ctx = makeContext({
            config: { multi_session_warning_enabled: false },
        });
        ctx.handleActiveSessionsUpdated({
            count: 2,
            warning_enabled: false,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }],
        });
        expect(ToastUtils.warning).not.toHaveBeenCalled();
        expect(ctx.multiSessionWarningActive).toBe(false);
    });

    it("resets and can toast again after dropping below two sessions", () => {
        const ctx = makeContext({ multiSessionWarningActive: true });
        ctx.handleActiveSessionsUpdated({
            count: 1,
            warning_enabled: true,
            sessions: [{ ip: "1.1.1.1" }],
        });
        expect(ctx.multiSessionWarningActive).toBe(false);
        ctx.handleActiveSessionsUpdated({
            count: 2,
            warning_enabled: true,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }],
        });
        expect(ToastUtils.warning).toHaveBeenCalledTimes(1);
        expect(ctx.multiSessionWarningActive).toBe(true);
    });

    it("uses config when warning_enabled is omitted from the payload", () => {
        const ctx = makeContext({
            config: { multi_session_warning_enabled: false },
        });
        ctx.handleActiveSessionsUpdated({
            count: 2,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }],
        });
        expect(ToastUtils.warning).not.toHaveBeenCalled();
    });
});
