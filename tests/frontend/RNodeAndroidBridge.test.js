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
            requestBluetoothPermissions: vi.fn().mockReturnValue("requested"),
            requestUsbPermissions: vi.fn().mockReturnValue("requested"),
        };
        const ab = new AndroidBridge(bridge, {});
        await expect(ab.requestPermission(AndroidBridge.PERM_BLUETOOTH)).resolves.toBe("requested");
        await expect(ab.requestPermission(AndroidBridge.PERM_USB)).resolves.toBe("requested");
        expect(bridge.requestBluetoothPermissions).toHaveBeenCalled();
        expect(bridge.requestUsbPermissions).toHaveBeenCalled();
    });

    it("hasNativeRNodeFlasher delegates to the bridge", () => {
        const bridge = { hasNativeRNodeFlasher: vi.fn().mockReturnValue(true), openRNodeFlasher: vi.fn() };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.hasNativeRNodeFlasher()).toBe(true);
        expect(ab.openRNodeFlasher()).toBe(true);
        expect(bridge.openRNodeFlasher).toHaveBeenCalled();
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

    it("getBatteryStatus delegates to the bridge", () => {
        const bridge = {
            getBatteryStatus: vi.fn().mockReturnValue('{"level":55,"charging":true}'),
        };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.getBatteryStatus()).toBe('{"level":55,"charging":true}');
        expect(bridge.getBatteryStatus).toHaveBeenCalled();
    });

    it("getBatteryStatus returns null when method missing", () => {
        const ab = new AndroidBridge({}, {});
        expect(ab.getBatteryStatus()).toBe(null);
    });

    it("auto-detects bridge from env.MeshChatXAndroid", () => {
        const env = { MeshChatXAndroid: { hasBluetoothPermissions: () => true } };
        const ab = new AndroidBridge(null, env);
        expect(ab.isAvailable()).toBe(true);
    });

    it("privacy helpers default to false when methods are missing", () => {
        const ab = new AndroidBridge({}, {});
        expect(ab.getBlockScreenshots()).toBe(false);
        expect(ab.getClearClipboardOnBackground()).toBe(false);
        expect(ab.setBlockScreenshots(true)).toBe(false);
        expect(ab.setClearClipboardOnBackground(true)).toBe(false);
    });

    it("privacy helpers delegate to the bridge", () => {
        const bridge = {
            getBlockScreenshots: vi.fn().mockReturnValue(true),
            setBlockScreenshots: vi.fn(),
            getClearClipboardOnBackground: vi.fn().mockReturnValue(false),
            setClearClipboardOnBackground: vi.fn(),
        };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.getBlockScreenshots()).toBe(true);
        expect(ab.getClearClipboardOnBackground()).toBe(false);
        expect(ab.setBlockScreenshots(true)).toBe(true);
        expect(ab.setClearClipboardOnBackground(true)).toBe(true);
        expect(bridge.setBlockScreenshots).toHaveBeenCalledWith(true);
        expect(bridge.setClearClipboardOnBackground).toHaveBeenCalledWith(true);
    });

    it("remote backend helpers default safely when methods are missing", () => {
        const ab = new AndroidBridge({}, {});
        expect(ab.getRemoteBackendUrl()).toBe("");
        expect(ab.getEffectiveBackendUrl()).toBe(null);
        expect(ab.isRemoteBackend()).toBe(false);
        expect(ab.setRemoteBackendUrlAndRestart("http://192.168.1.10:9337")).toBe("unsupported");
    });

    it("remote backend helpers delegate to the bridge", () => {
        const bridge = {
            getRemoteBackendUrl: vi.fn().mockReturnValue("http://192.168.1.10:9337"),
            getEffectiveBackendUrl: vi.fn().mockReturnValue("http://192.168.1.10:9337"),
            isRemoteBackend: vi.fn().mockReturnValue(true),
            setRemoteBackendUrlAndRestart: vi.fn().mockReturnValue("ok"),
        };
        const ab = new AndroidBridge(bridge, {});
        expect(ab.getRemoteBackendUrl()).toBe("http://192.168.1.10:9337");
        expect(ab.getEffectiveBackendUrl()).toBe("http://192.168.1.10:9337");
        expect(ab.isRemoteBackend()).toBe(true);
        expect(ab.setRemoteBackendUrlAndRestart("http://10.0.0.2:8000")).toBe("ok");
        expect(bridge.setRemoteBackendUrlAndRestart).toHaveBeenCalledWith("http://10.0.0.2:8000");
    });
});
