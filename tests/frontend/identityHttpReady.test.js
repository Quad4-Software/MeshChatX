import { afterEach, describe, expect, it, vi } from "vitest";
import GlobalState from "@/js/GlobalState";
import { isIdentityHttpReady, runWhenIdentityHttpReady } from "@/js/identityHttpReady.js";

describe("identityHttpReady", () => {
    const snapshot = {
        networkReady: GlobalState.networkReady,
        networkDegraded: GlobalState.networkDegraded,
        networkStarting: GlobalState.networkStarting,
    };

    afterEach(() => {
        GlobalState.networkReady = snapshot.networkReady;
        GlobalState.networkDegraded = snapshot.networkDegraded;
        GlobalState.networkStarting = snapshot.networkStarting;
    });

    it("is not ready while networkStarting without ready/degraded", () => {
        GlobalState.networkReady = false;
        GlobalState.networkDegraded = false;
        GlobalState.networkStarting = true;
        expect(isIdentityHttpReady()).toBe(false);
    });

    it("is ready when networkReady", () => {
        GlobalState.networkReady = true;
        GlobalState.networkDegraded = false;
        GlobalState.networkStarting = true;
        expect(isIdentityHttpReady()).toBe(true);
    });

    it("is ready when degraded", () => {
        GlobalState.networkReady = false;
        GlobalState.networkDegraded = true;
        GlobalState.networkStarting = true;
        expect(isIdentityHttpReady()).toBe(true);
    });

    it("is ready when startup finished without ready flag", () => {
        GlobalState.networkReady = false;
        GlobalState.networkDegraded = false;
        GlobalState.networkStarting = false;
        expect(isIdentityHttpReady()).toBe(true);
    });

    it("runs callback immediately when already ready", () => {
        GlobalState.networkReady = true;
        GlobalState.networkStarting = false;
        const cb = vi.fn();
        const stop = runWhenIdentityHttpReady(cb);
        expect(cb).toHaveBeenCalledTimes(1);
        expect(stop).toBeNull();
    });

    it("defers callback until networkReady", async () => {
        GlobalState.networkReady = false;
        GlobalState.networkDegraded = false;
        GlobalState.networkStarting = true;
        const cb = vi.fn();
        const stop = runWhenIdentityHttpReady(cb);
        expect(cb).not.toHaveBeenCalled();
        expect(typeof stop).toBe("function");
        GlobalState.networkReady = true;
        GlobalState.networkStarting = false;
        await Promise.resolve();
        expect(cb).toHaveBeenCalledTimes(1);
        stop?.();
    });
});
