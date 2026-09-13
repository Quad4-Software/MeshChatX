// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach } from "vitest";
import { handleActiveSessionsUpdated } from "../../meshchatx/src/frontend/features/app-shell/lib/appShellNav.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.js";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

function makeState(overrides = {}) {
    return {
        config: { multi_session_warning_enabled: true },
        multiSessionWarningActive: false,
        ...overrides,
    };
}

describe("App multi-session warning toast", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            app: {
                multi_session_warning: "multi {count}",
            },
        });
    });

    it("toasts when two sessions connect and setting is enabled", () => {
        const state = makeState();
        handleActiveSessionsUpdated(state, {
            count: 2,
            warning_enabled: true,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }],
        });
        expect(ToastUtils.warning).toHaveBeenCalledWith("multi 2");
        expect(state.multiSessionWarningActive).toBe(true);
    });

    it("does not toast for localhost or lan-only sessions", () => {
        const state = makeState();
        handleActiveSessionsUpdated(state, {
            count: 2,
            warning_enabled: true,
            sessions: [{ ip: "127.0.0.1" }, { ip: "192.168.1.10" }],
        });
        expect(ToastUtils.warning).not.toHaveBeenCalled();
        expect(state.multiSessionWarningActive).toBe(false);
    });

    it("does not toast again while still above the threshold", () => {
        const state = makeState({ multiSessionWarningActive: true });
        handleActiveSessionsUpdated(state, {
            count: 3,
            warning_enabled: true,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }, { ip: "3.3.3.3" }],
        });
        expect(ToastUtils.warning).not.toHaveBeenCalled();
        expect(state.multiSessionWarningActive).toBe(true);
    });

    it("does not toast when the setting is disabled", () => {
        const state = makeState({
            config: { multi_session_warning_enabled: false },
        });
        handleActiveSessionsUpdated(state, {
            count: 2,
            warning_enabled: false,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }],
        });
        expect(ToastUtils.warning).not.toHaveBeenCalled();
        expect(state.multiSessionWarningActive).toBe(false);
    });

    it("resets and can toast again after dropping below two sessions", () => {
        const state = makeState({ multiSessionWarningActive: true });
        handleActiveSessionsUpdated(state, {
            count: 1,
            warning_enabled: true,
            sessions: [{ ip: "1.1.1.1" }],
        });
        expect(state.multiSessionWarningActive).toBe(false);
        handleActiveSessionsUpdated(state, {
            count: 2,
            warning_enabled: true,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }],
        });
        expect(ToastUtils.warning).toHaveBeenCalledTimes(1);
        expect(state.multiSessionWarningActive).toBe(true);
    });

    it("uses config when warning_enabled is omitted from the payload", () => {
        const state = makeState({
            config: { multi_session_warning_enabled: false },
        });
        handleActiveSessionsUpdated(state, {
            count: 2,
            sessions: [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }],
        });
        expect(ToastUtils.warning).not.toHaveBeenCalled();
    });
});
