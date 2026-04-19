/**
 * Thin JS wrapper around the native MeshChatXAndroid bridge.
 *
 * The bridge methods are added by the Android WebView side
 * (see android/app/src/main/java/com/meshchatx/MainActivity.java).
 * Each method may be missing on older builds, so all helpers degrade
 * gracefully and return safe defaults.
 *
 * The wrapper is also fully testable: a custom bridge object can be
 * injected via the constructor.
 */

const PERM_BLUETOOTH = "bluetooth";
const PERM_USB = "usb";

function pickEnv() {
    if (typeof window !== "undefined") {
        return window;
    }
    if (typeof globalThis !== "undefined") {
        return globalThis;
    }
    return {};
}

function safeCall(fn, fallback) {
    try {
        const result = fn();
        return result === undefined ? fallback : result;
    } catch {
        return fallback;
    }
}

export default class AndroidBridge {
    constructor(bridge = null, env = null) {
        this.env = env || pickEnv();
        this.bridge = bridge || this.env.MeshChatXAndroid || null;
    }

    isAvailable() {
        return Boolean(this.bridge);
    }

    /**
     * Check whether a runtime permission group is currently granted on the
     * Android host. Returns true on non-android (no-op) so calling code
     * can chain checks without branching.
     */
    hasPermission(permissionGroup) {
        if (!this.bridge) {
            return true;
        }
        if (permissionGroup === PERM_BLUETOOTH && typeof this.bridge.hasBluetoothPermissions === "function") {
            return safeCall(() => Boolean(this.bridge.hasBluetoothPermissions()), false);
        }
        if (permissionGroup === PERM_USB && typeof this.bridge.hasUsbPermissions === "function") {
            return safeCall(() => Boolean(this.bridge.hasUsbPermissions()), false);
        }
        return false;
    }

    /**
     * Request a runtime permission group from Android. Resolves to true if
     * the permission was already granted (or the call was made on a non-
     * android build). The actual grant result is delivered asynchronously
     * by the OS, so callers should re-check via hasPermission afterwards.
     */
    async requestPermission(permissionGroup) {
        if (!this.bridge) {
            return true;
        }
        if (permissionGroup === PERM_BLUETOOTH && typeof this.bridge.requestBluetoothPermissions === "function") {
            return safeCall(() => {
                this.bridge.requestBluetoothPermissions();
                return true;
            }, false);
        }
        if (permissionGroup === PERM_USB && typeof this.bridge.requestUsbPermissions === "function") {
            return safeCall(() => {
                this.bridge.requestUsbPermissions();
                return true;
            }, false);
        }
        return false;
    }

    openBluetoothSettings() {
        if (!this.bridge || typeof this.bridge.openBluetoothSettings !== "function") {
            return false;
        }
        return safeCall(() => {
            this.bridge.openBluetoothSettings();
            return true;
        }, false);
    }

    openUsbSettings() {
        if (!this.bridge || typeof this.bridge.openUsbSettings !== "function") {
            return false;
        }
        return safeCall(() => {
            this.bridge.openUsbSettings();
            return true;
        }, false);
    }

    getPlatform() {
        if (!this.bridge || typeof this.bridge.getPlatform !== "function") {
            return null;
        }
        return safeCall(() => this.bridge.getPlatform(), null);
    }
}

AndroidBridge.PERM_BLUETOOTH = PERM_BLUETOOTH;
AndroidBridge.PERM_USB = PERM_USB;
