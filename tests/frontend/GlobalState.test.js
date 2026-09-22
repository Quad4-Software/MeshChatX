import { describe, it, expect, vi } from "vitest";
import globalState, {
    batchGlobalState,
    mergeGlobalConfig,
    subscribeGlobalState,
} from "../../meshchatx/src/frontend/js/GlobalState";

describe("GlobalState proxy cache", () => {
    it("returns the same nested proxy on repeated reads", () => {
        const first = globalState.config;
        const second = globalState.config;
        expect(first).toBe(second);
    });

    it("keeps nested object identity stable across unrelated writes", () => {
        const before = globalState.config;
        globalState.unreadConversationsCount = (globalState.unreadConversationsCount || 0) + 1;
        expect(globalState.config).toBe(before);
    });
});

describe("GlobalState notifications", () => {
    it("notifies once per real change", () => {
        const listener = vi.fn();
        const unsubscribe = subscribeGlobalState(listener);
        try {
            globalState.relayChatUnreadCount = (globalState.relayChatUnreadCount || 0) + 1;
            expect(listener).toHaveBeenCalledTimes(1);
        } finally {
            unsubscribe();
        }
    });

    it("does not notify when a set writes the same value", () => {
        const listener = vi.fn();
        const unsubscribe = subscribeGlobalState(listener);
        try {
            const current = globalState.activeCallTab;
            globalState.activeCallTab = current;
            expect(listener).not.toHaveBeenCalled();
        } finally {
            unsubscribe();
        }
    });

    it("coalesces mutations inside batchGlobalState into a single notification", () => {
        const listener = vi.fn();
        const unsubscribe = subscribeGlobalState(listener);
        try {
            batchGlobalState(() => {
                globalState.missedCallsCount = (globalState.missedCallsCount || 0) + 1;
                globalState.networkDegraded = !globalState.networkDegraded;
                globalState.demoMode = !globalState.demoMode;
            });
            expect(listener).toHaveBeenCalledTimes(1);
        } finally {
            unsubscribe();
        }
    });

    it("flushes a pending notify once the outermost batch ends", () => {
        const listener = vi.fn();
        const unsubscribe = subscribeGlobalState(listener);
        try {
            batchGlobalState(() => {
                batchGlobalState(() => {
                    globalState.networkStarting = !globalState.networkStarting;
                });
                globalState.networkReady = !globalState.networkReady;
            });
            expect(listener).toHaveBeenCalledTimes(1);
        } finally {
            unsubscribe();
        }
    });

    it("still flushes the pending notify when the batch body throws", () => {
        const listener = vi.fn();
        const unsubscribe = subscribeGlobalState(listener);
        try {
            expect(() =>
                batchGlobalState(() => {
                    globalState.demoMode = !globalState.demoMode;
                    throw new Error("boom");
                })
            ).toThrow("boom");
            expect(listener).toHaveBeenCalledTimes(1);
        } finally {
            unsubscribe();
        }
    });

    it("mergeGlobalConfig emits a single notification", () => {
        const listener = vi.fn();
        const unsubscribe = subscribeGlobalState(listener);
        try {
            mergeGlobalConfig({ ui_transparency: 0.25, demoMode: true });
            expect(listener).toHaveBeenCalledTimes(1);
            expect(globalState.config.ui_transparency).toBe(0.25);
        } finally {
            unsubscribe();
        }
    });
});
