import { describe, it, expect, vi } from "vitest";
import AndroidBridge from "@/js/rnode/AndroidBridge.js";

describe("AndroidBridge", () => {
    it("reports unavailable when no bridge is provided", () => {
        const ab = new AndroidBridge(null, {});
        expect(ab.isAvailable()).toBe(false);
        expect(ab.openBluetoothSettings()).toBe(false);
        expect(ab.openUsbSettings()).toBe(false);
        expect(ab.getPlatform()).toBe(null);
    });

    it("returns true for hasPermission when no bridge is present (no-op host)", () => {
        const ab = new AndroidBridge(null, {});
        expect(ab.hasPermission(AndroidBridge.PERM_BLUETOOTH)).toBe(true);
        expect(ab.hasPermission(AndroidBridge.PERM_USB)).toBe(true);
    });

    it("delegates hasBluetoothPermissions to the bridge", () => {
        const bridge = { hasBluetoothPermissions: vi.fn().mockReturnValue(true) };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.hasPermission(AndroidBridge.PERM_BLUETOOTH)).toBe(true);
        expect(bridge.hasBluetoothPermissions).toHaveBeenCalled();
    });

    it("delegates hasUsbPermissions to the bridge", () => {
        const bridge = { hasUsbPermissions: vi.fn().mockReturnValue(false) };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.hasPermission(AndroidBridge.PERM_USB)).toBe(false);
    });

    it("requestPermission triggers the appropriate bridge method", async () => {
        const bridge = {
            requestBluetoothPermissions: vi.fn(),
            requestUsbPermissions: vi.fn(),
        };
        const ab = new AndroidBridge(bridge, {});
        await ab.requestPermission(AndroidBridge.PERM_BLUETOOTH);
        await ab.requestPermission(AndroidBridge.PERM_USB);
        expect(bridge.requestBluetoothPermissions).toHaveBeenCalled();
        expect(bridge.requestUsbPermissions).toHaveBeenCalled();
    });

    it("settings helpers return true when bridge accepts the call", () => {
        const bridge = {
            openBluetoothSettings: vi.fn(),
            openUsbSettings: vi.fn(),
        };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.openBluetoothSettings()).toBe(true);
        expect(ab.openUsbSettings()).toBe(true);
    });

    it("settings helpers swallow exceptions and return false", () => {
        const bridge = {
            openBluetoothSettings: () => {
                throw new Error("nope");
            },
            openUsbSettings: () => {
                throw new Error("nope");
            },
        };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.openBluetoothSettings()).toBe(false);
        expect(ab.openUsbSettings()).toBe(false);
    });

    it("getPlatform delegates to the bridge", () => {
        const bridge = { getPlatform: vi.fn().mockReturnValue("android") };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.getPlatform()).toBe("android");
    });

    it("auto-detects bridge from env.MeshChatXAndroid", () => {
        const env = { MeshChatXAndroid: { hasBluetoothPermissions: () => true } };
        const ab = new AndroidBridge(null, env);
        expect(ab.isAvailable()).toBe(true);
    });
});
