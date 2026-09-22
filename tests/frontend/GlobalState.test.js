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

describe("GlobalState key-scoped subscriptions", () => {
    it("fires only for the subscribed domain", async () => {
        const { subscribeGlobalStateKey } = await import(
            "../../meshchatx/src/frontend/js/GlobalState"
        );
        const configListener = vi.fn();
        const unsubscribe = subscribeGlobalStateKey("config", configListener);
        try {
            globalState.relayChatUnreadCount = (globalState.relayChatUnreadCount || 0) + 1;
            expect(configListener).not.toHaveBeenCalled();
            globalState.config.some_new_key = "v";
            expect(configListener).toHaveBeenCalledTimes(1);
            delete globalState.config.some_new_key;
        } finally {
            unsubscribe();
        }
    });

    it("fires on whole-config replacement", async () => {
        const { subscribeGlobalStateKey } = await import(
            "../../meshchatx/src/frontend/js/GlobalState"
        );
        const listener = vi.fn();
        const unsubscribe = subscribeGlobalStateKey("config", listener);
        try {
            mergeGlobalConfig({ scoped_replace_probe: true });
            expect(listener).toHaveBeenCalled();
            delete globalState.config.scoped_replace_probe;
        } finally {
            unsubscribe();
        }
    });

    it("delivers batched key notifications on flush", async () => {
        const { subscribeGlobalStateKey } = await import(
            "../../meshchatx/src/frontend/js/GlobalState"
        );
        const listener = vi.fn();
        const unsubscribe = subscribeGlobalStateKey("config", listener);
        try {
            batchGlobalState(() => {
                globalState.config.batch_probe_a = 1;
                globalState.config.batch_probe_b = 2;
            });
            expect(listener).toHaveBeenCalledTimes(1);
            delete globalState.config.batch_probe_a;
            delete globalState.config.batch_probe_b;
        } finally {
            unsubscribe();
        }
    });
});
