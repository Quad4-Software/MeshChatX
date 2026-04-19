/**
 * Runtime capability detection for RNode flasher.
 *
 * Determines which connection transports are available in the current
 * environment (Web Serial, Web Bluetooth, WebUSB polyfill, WiFi/HTTP)
 * and exposes structured reasons when something is unsupported so the UI
 * can render actionable guidance.
 *
 * Pure functions, no DOM mutation, safe to import in tests.
 */

export const TRANSPORT_SERIAL = "serial";
export const TRANSPORT_BLUETOOTH = "bluetooth";
export const TRANSPORT_WIFI = "wifi";

const ANDROID_RE = /android/i;
const ELECTRON_RE = /electron/i;

function pickGlobal(provided) {
    if (provided) {
        return provided;
    }
    if (typeof window !== "undefined") {
        return window;
    }
    if (typeof globalThis !== "undefined") {
        return globalThis;
    }
    return {};
}

function detectPlatform(env) {
    const ua = env.navigator?.userAgent ?? "";
    const isAndroid = ANDROID_RE.test(ua);
    const isElectron = ELECTRON_RE.test(ua) || Boolean(env.electron);
    const hasMeshChatXAndroid = Boolean(env.MeshChatXAndroid);
    return {
        isAndroid,
        isElectron,
        hasMeshChatXAndroid,
        isSecureContext: Boolean(env.isSecureContext),
        userAgent: ua,
    };
}

function detectSerial(env, platform) {
    const hasNative = Boolean(env.navigator?.serial);
    const hasUsbPolyfillTarget = Boolean(env.navigator?.usb);
    const hasPolyfillModule = Boolean(env.serial);

    if (hasNative) {
        return {
            available: true,
            kind: "native",
            polyfilled: false,
            reason: null,
        };
    }
    if (hasUsbPolyfillTarget && hasPolyfillModule) {
        return {
            available: true,
            kind: "polyfill",
            polyfilled: true,
            reason: null,
        };
    }
    if (hasUsbPolyfillTarget && !hasPolyfillModule) {
        return {
            available: false,
            kind: "polyfill-pending",
            polyfilled: false,
            reason: "polyfill_not_loaded",
        };
    }
    if (platform.isAndroid) {
        return {
            available: false,
            kind: "none",
            polyfilled: false,
            reason: "android_webview_no_serial",
        };
    }
    return {
        available: false,
        kind: "none",
        polyfilled: false,
        reason: "browser_unsupported",
    };
}

function detectBluetooth(env, platform) {
    const hasNative = Boolean(env.navigator?.bluetooth);
    if (hasNative) {
        return {
            available: true,
            kind: "web-bluetooth",
            reason: null,
        };
    }
    if (platform.hasMeshChatXAndroid) {
        return {
            available: false,
            kind: "android-bridge",
            reason: "android_bridge_not_implemented",
        };
    }
    return {
        available: false,
        kind: "none",
        reason: platform.isSecureContext ? "browser_unsupported" : "insecure_context",
    };
}

function detectWifi() {
    return {
        available: true,
        kind: "http",
        reason: null,
    };
}

/**
 * Inspect the environment and return a capabilities snapshot.
 *
 * @param {object} [overrides]
 * @param {object} [overrides.env] alternative global object (window-like) for tests
 * @returns {{
 *   platform: object,
 *   transports: { serial: object, bluetooth: object, wifi: object },
 *   anyAvailable: boolean,
 * }}
 */
export function detectCapabilities(overrides = {}) {
    const env = pickGlobal(overrides.env);
    const platform = detectPlatform(env);
    const transports = {
        [TRANSPORT_SERIAL]: detectSerial(env, platform),
        [TRANSPORT_BLUETOOTH]: detectBluetooth(env, platform),
        [TRANSPORT_WIFI]: detectWifi(),
    };
    const anyAvailable =
        transports[TRANSPORT_SERIAL].available ||
        transports[TRANSPORT_BLUETOOTH].available ||
        transports[TRANSPORT_WIFI].available;
    return { platform, transports, anyAvailable };
}

/**
 * Choose the most appropriate default transport given current capabilities.
 *
 * Order of preference: native serial, polyfill serial, web bluetooth, wifi.
 */
export function pickDefaultTransport(capabilities) {
    const t = capabilities?.transports ?? {};
    if (t[TRANSPORT_SERIAL]?.available) {
        return TRANSPORT_SERIAL;
    }
    if (t[TRANSPORT_BLUETOOTH]?.available) {
        return TRANSPORT_BLUETOOTH;
    }
    return TRANSPORT_WIFI;
}

/**
 * Return a list of human-readable, translation-aware suggestions for a
 * transport that is unavailable. The caller maps these keys to i18n strings.
 */
export function transportSuggestionKeys(capabilities, transportName) {
    const transport = capabilities?.transports?.[transportName];
    if (!transport || transport.available) {
        return [];
    }
    const platform = capabilities.platform ?? {};
    const reason = transport.reason ?? "unknown";
    const suggestions = [`tools.rnode_flasher.support.${transportName}.${reason}`];
    if (transportName === TRANSPORT_SERIAL && platform.isAndroid) {
        suggestions.push("tools.rnode_flasher.support.serial.android_use_chrome");
    }
    if (transportName === TRANSPORT_BLUETOOTH && !platform.isSecureContext) {
        suggestions.push("tools.rnode_flasher.support.bluetooth.requires_https");
    }
    return suggestions;
}

export default {
    detectCapabilities,
    pickDefaultTransport,
    transportSuggestionKeys,
    TRANSPORT_SERIAL,
    TRANSPORT_BLUETOOTH,
    TRANSPORT_WIFI,
};
