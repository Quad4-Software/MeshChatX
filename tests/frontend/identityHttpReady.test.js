import { afterEach, describe, expect, it, vi } from "vitest";
import { isIdentityHttpReady, runWhenIdentityHttpReady } from "@/js/identityHttpReady.js";
import { useNetworkStore } from "@/js/stores/networkStore.js";

describe("identityHttpReady", () => {
    const snapshot = {
        networkReady: useNetworkStore().networkReady,
        networkDegraded: useNetworkStore().networkDegraded,
        networkStarting: useNetworkStore().networkStarting,
    };

    afterEach(() => {
        useNetworkStore().networkReady = snapshot.networkReady;
        useNetworkStore().networkDegraded = snapshot.networkDegraded;
        useNetworkStore().networkStarting = snapshot.networkStarting;
    });

    it("is not ready while networkStarting without ready/degraded", () => {
        useNetworkStore().networkReady = false;
        useNetworkStore().networkDegraded = false;
        useNetworkStore().networkStarting = true;
        expect(isIdentityHttpReady()).toBe(false);
    });

    it("is ready when networkReady", () => {
        useNetworkStore().networkReady = true;
        useNetworkStore().networkDegraded = false;
        useNetworkStore().networkStarting = true;
        expect(isIdentityHttpReady()).toBe(true);
    });

    it("is ready when degraded", () => {
        useNetworkStore().networkReady = false;
        useNetworkStore().networkDegraded = true;
        useNetworkStore().networkStarting = true;
        expect(isIdentityHttpReady()).toBe(true);
    });

    it("is ready when startup finished without ready flag", () => {
        useNetworkStore().networkReady = false;
        useNetworkStore().networkDegraded = false;
        useNetworkStore().networkStarting = false;
        expect(isIdentityHttpReady()).toBe(true);
    });

    it("runs callback immediately when already ready", () => {
        useNetworkStore().networkReady = true;
        useNetworkStore().networkStarting = false;
        const cb = vi.fn();
        const stop = runWhenIdentityHttpReady(cb);
        expect(cb).toHaveBeenCalledTimes(1);
        expect(stop).toBeNull();
    });

    it("defers callback until networkReady", async () => {
        useNetworkStore().networkReady = false;
        useNetworkStore().networkDegraded = false;
        useNetworkStore().networkStarting = true;
        const cb = vi.fn();
        const stop = runWhenIdentityHttpReady(cb);
        expect(cb).not.toHaveBeenCalled();
        expect(typeof stop).toBe("function");
        useNetworkStore().networkReady = true;
        useNetworkStore().networkStarting = false;
        await Promise.resolve();
        expect(cb).toHaveBeenCalledTimes(1);
        stop?.();
    });
});
