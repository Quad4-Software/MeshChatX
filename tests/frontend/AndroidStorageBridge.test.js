import { describe, it, expect, vi, beforeEach } from "vitest";
import AndroidStorageBridge from "../../meshchatx/src/frontend/js/AndroidStorageBridge.js";

describe("AndroidStorageBridge", () => {
    let bridge;

    beforeEach(() => {
        bridge = new AndroidStorageBridge({
            getPlatform: () => "android",
            getAndroidStorageStatus: () =>
                JSON.stringify({
                    needs_setup_choice: true,
                    active_mode: "external",
                }),
            setAndroidStorageMode: vi.fn(),
            markAndroidStorageSetupCompleted: vi.fn(),
            restartApp: vi.fn(),
        });
    });

    it("getStatus parses JSON from native bridge", () => {
        expect(bridge.getStatus()).toEqual({
            needs_setup_choice: true,
            active_mode: "external",
        });
    });

    it("applySetupChoice restarts when mode differs from active", () => {
        const native = bridge.android.bridge;
        const result = bridge.applySetupChoice("internal", { active_mode: "external" });
        expect(native.setAndroidStorageMode).toHaveBeenCalledWith("internal");
        expect(native.markAndroidStorageSetupCompleted).toHaveBeenCalled();
        expect(native.restartApp).toHaveBeenCalled();
        expect(result.restarted).toBe(true);
    });

    it("applySetupChoice skips restart when mode matches active", () => {
        const native = bridge.android.bridge;
        const result = bridge.applySetupChoice("external", { active_mode: "external" });
        expect(native.restartApp).not.toHaveBeenCalled();
        expect(result.restarted).toBe(false);
    });
});
