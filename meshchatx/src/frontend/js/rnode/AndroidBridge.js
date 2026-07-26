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
     * Request a runtime permission group from Android.
     * Resolves to a status string: granted | requested | settings | unsupported | true (legacy).
     */
    async requestPermission(permissionGroup) {
        if (!this.bridge) {
            return "granted";
        }
        if (permissionGroup === PERM_BLUETOOTH && typeof this.bridge.requestBluetoothPermissions === "function") {
            return safeCall(() => {
                const result = this.bridge.requestBluetoothPermissions();
                if (typeof result === "string") {
                    return result;
                }
                return "requested";
            }, "unsupported");
        }
        if (permissionGroup === PERM_USB && typeof this.bridge.requestUsbPermissions === "function") {
            return safeCall(() => {
                const result = this.bridge.requestUsbPermissions();
                if (typeof result === "string") {
                    return result;
                }
                return "requested";
            }, "unsupported");
        }
        return "unsupported";
    }

    hasAndroidSerial() {
        return this.hasNativeRNodeFlasher();
    }

    hasNativeRNodeFlasher() {
        if (!this.bridge || typeof this.bridge.hasNativeRNodeFlasher !== "function") {
            return false;
        }
        return safeCall(() => Boolean(this.bridge.hasNativeRNodeFlasher()), false);
    }

    openRNodeFlasher() {
        if (!this.bridge || typeof this.bridge.openRNodeFlasher !== "function") {
            return false;
        }
        return safeCall(() => {
            const result = this.bridge.openRNodeFlasher();
            if (typeof result === "string") {
                return result === "ok" || result === "requested";
            }
            return true;
        }, false);
    }

    openBluetoothSettings() {
        if (!this.bridge || typeof this.bridge.openBluetoothSettings !== "function") {
            return false;
        }
        return safeCall(() => {
            const result = this.bridge.openBluetoothSettings();
            if (typeof result === "string") {
                return result === "ok" || result === "settings";
            }
            return true;
        }, false);
    }

    openUsbSettings() {
        if (!this.bridge || typeof this.bridge.openUsbSettings !== "function") {
            return false;
        }
        return safeCall(() => {
            const result = this.bridge.openUsbSettings();
            if (typeof result === "string") {
                return result === "ok" || result === "settings";
            }
            return true;
        }, false);
    }

    getPlatform() {
        if (!this.bridge || typeof this.bridge.getPlatform !== "function") {
            return null;
        }
        return safeCall(() => this.bridge.getPlatform(), null);
    }

    /**
     * Host battery status JSON string from the Android WebView bridge.
     * Returns null when unavailable.
     */
    getBatteryStatus() {
        if (!this.bridge || typeof this.bridge.getBatteryStatus !== "function") {
            return null;
        }
        return safeCall(() => this.bridge.getBatteryStatus(), null);
    }

    getSidebandPluginsDefaultPath() {
        if (!this.bridge || typeof this.bridge.getSidebandPluginsDefaultPath !== "function") {
            return null;
        }
        return safeCall(() => this.bridge.getSidebandPluginsDefaultPath(), null);
    }

    /**
     * Opens the system share sheet with the installed APK (Bluetooth, Nearby Share, etc.).
     * No-op when bridge or method is missing.
     */
    shareApk() {
        if (!this.bridge || typeof this.bridge.shareApk !== "function") {
            return false;
        }
        return safeCall(() => {
            this.bridge.shareApk();
            return true;
        }, false);
    }

    /**
     * Whether FLAG_SECURE is enabled (blocks screenshots and recent-app previews).
     * Defaults to false when the bridge method is missing.
     */
    getBlockScreenshots() {
        if (!this.bridge || typeof this.bridge.getBlockScreenshots !== "function") {
            return false;
        }
        return safeCall(() => Boolean(this.bridge.getBlockScreenshots()), false);
    }

    setBlockScreenshots(enabled) {
        if (!this.bridge || typeof this.bridge.setBlockScreenshots !== "function") {
            return false;
        }
        return safeCall(() => {
            this.bridge.setBlockScreenshots(Boolean(enabled));
            return true;
        }, false);
    }

    /**
     * Whether the primary clipboard is cleared when the app goes to the background.
     * Defaults to false when the bridge method is missing.
     */
    getClearClipboardOnBackground() {
        if (!this.bridge || typeof this.bridge.getClearClipboardOnBackground !== "function") {
            return false;
        }
        return safeCall(() => Boolean(this.bridge.getClearClipboardOnBackground()), false);
    }

    setClearClipboardOnBackground(enabled) {
        if (!this.bridge || typeof this.bridge.setClearClipboardOnBackground !== "function") {
            return false;
        }
        return safeCall(() => {
            this.bridge.setClearClipboardOnBackground(Boolean(enabled));
            return true;
        }, false);
    }

    /**
     * Configured remote backend URL, or empty string for the on-device local backend.
     */
    getRemoteBackendUrl() {
        if (!this.bridge || typeof this.bridge.getRemoteBackendUrl !== "function") {
            return "";
        }
        return safeCall(() => String(this.bridge.getRemoteBackendUrl() || ""), "");
    }

    getEffectiveBackendUrl() {
        if (!this.bridge || typeof this.bridge.getEffectiveBackendUrl !== "function") {
            return null;
        }
        return safeCall(() => this.bridge.getEffectiveBackendUrl(), null);
    }

    isRemoteBackend() {
        if (!this.bridge || typeof this.bridge.isRemoteBackend !== "function") {
            return false;
        }
        return safeCall(() => Boolean(this.bridge.isRemoteBackend()), false);
    }

    /**
     * Persist remote backend URL and restart the Android shell.
     * Empty string clears to local. Returns ok | invalid | unchanged | unsupported.
     */
    setRemoteBackendUrlAndRestart(url) {
        if (!this.bridge || typeof this.bridge.setRemoteBackendUrlAndRestart !== "function") {
            return "unsupported";
        }
        return safeCall(() => {
            const result = this.bridge.setRemoteBackendUrlAndRestart(url == null ? "" : String(url));
            return typeof result === "string" ? result : "unsupported";
        }, "unsupported");
    }
}

AndroidBridge.PERM_BLUETOOTH = PERM_BLUETOOTH;
AndroidBridge.PERM_USB = PERM_USB;
