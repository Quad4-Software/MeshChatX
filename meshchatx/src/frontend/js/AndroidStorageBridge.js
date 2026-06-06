/**
 * Android app-specific storage location (internal vs external files dir).
 */

import AndroidBridge from "./rnode/AndroidBridge.js";

function pickEnv() {
    if (typeof window !== "undefined") {
        return window;
    }
    if (typeof globalThis !== "undefined") {
        return globalThis;
    }
    return {};
}

function safeParseJson(raw, fallback) {
    if (raw == null || raw === "") {
        return fallback;
    }
    try {
        return JSON.parse(raw);
    } catch {
        return fallback;
    }
}

export default class AndroidStorageBridge {
    constructor(bridge = null, env = null) {
        this.android = new AndroidBridge(bridge, env || pickEnv());
    }

    isAndroidHost() {
        if (!this.android.isAvailable()) {
            return false;
        }
        const bridge = this.android.bridge;
        if (typeof bridge?.getPlatform === "function") {
            try {
                return bridge.getPlatform() === "android";
            } catch {
                return false;
            }
        }
        return typeof bridge?.getAndroidStorageStatus === "function";
    }

    getStatus() {
        if (!this.isAndroidHost()) {
            return null;
        }
        const bridge = this.android.bridge;
        if (typeof bridge.getAndroidStorageStatus !== "function") {
            return null;
        }
        try {
            return safeParseJson(bridge.getAndroidStorageStatus(), null);
        } catch {
            return null;
        }
    }

    setMode(mode) {
        const bridge = this.android.bridge;
        if (typeof bridge?.setAndroidStorageMode !== "function") {
            return false;
        }
        try {
            bridge.setAndroidStorageMode(mode);
            return true;
        } catch {
            return false;
        }
    }

    scheduleCopyToExternalAndRestart() {
        const bridge = this.android.bridge;
        if (typeof bridge?.scheduleCopyToExternalAndRestart !== "function") {
            return false;
        }
        try {
            bridge.scheduleCopyToExternalAndRestart();
            return true;
        } catch {
            return false;
        }
    }

    keepInternalAndDismiss() {
        const bridge = this.android.bridge;
        if (typeof bridge?.keepInternalStorageAndDismiss !== "function") {
            return false;
        }
        try {
            bridge.keepInternalStorageAndDismiss();
            return true;
        } catch {
            return false;
        }
    }

    restartApp() {
        const bridge = this.android.bridge;
        if (typeof bridge?.restartApp === "function") {
            try {
                bridge.restartApp();
                return true;
            } catch {
                // fall through
            }
        }
        if (typeof bridge?.exitApp === "function") {
            try {
                bridge.exitApp();
                return true;
            } catch {
                return false;
            }
        }
        return false;
    }

    /**
     * Apply setup choice; restart when active mode differs from selection.
     */
    applySetupChoice(mode, status) {
        if (!status) {
            return { restarted: false };
        }
        const active = status.active_mode;
        this.setMode(mode);
        if (typeof this.android.bridge?.markAndroidStorageSetupCompleted === "function") {
            try {
                this.android.bridge.markAndroidStorageSetupCompleted();
            } catch {
                // optional on older builds
            }
        }
        if (active !== mode) {
            this.restartApp();
            return { restarted: true };
        }
        return { restarted: false };
    }
}

export function restartMeshChatAndroid() {
    const bridge = new AndroidStorageBridge();
    return bridge.restartApp();
}
