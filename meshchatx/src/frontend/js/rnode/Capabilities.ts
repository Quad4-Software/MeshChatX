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

export type RNodeTransportName = typeof TRANSPORT_SERIAL | typeof TRANSPORT_BLUETOOTH | typeof TRANSPORT_WIFI;

export type CapabilityPlatform = {
    isAndroid: boolean;
    isElectron: boolean;
    hasMeshChatXAndroid: boolean;
    isBrave: boolean;
    isSecureContext: boolean;
    userAgent: string;
};

export type TransportCapability = {
    available: boolean;
    kind: string;
    polyfilled?: boolean;
    reason: string | null;
};

export type CapabilitiesSnapshot = {
    platform: CapabilityPlatform;
    transports: {
        serial: TransportCapability;
        bluetooth: TransportCapability;
        wifi: TransportCapability;
    };
    anyAvailable: boolean;
};

export type DetectCapabilitiesOverrides = {
    env?: Record<string, any>;
};

const ANDROID_RE = /android/i;
const ELECTRON_RE = /electron/i;

function pickGlobal(provided?: Record<string, any> | null): Record<string, any> {
    if (provided) {
        return provided;
    }
    if (typeof window !== "undefined") {
        return window as unknown as Record<string, any>;
    }
    if (typeof globalThis !== "undefined") {
        return globalThis as unknown as Record<string, any>;
    }
    return {};
}

function detectPlatform(env: Record<string, any>): CapabilityPlatform {
    const ua = env.navigator?.userAgent ?? "";
    const isAndroid = ANDROID_RE.test(ua);
    const isElectron = ELECTRON_RE.test(ua) || Boolean(env.electron);
    const hasMeshChatXAndroid = Boolean(env.MeshChatXAndroid);
    const isBrave = /Brave/i.test(ua) || Boolean(env.navigator?.brave) || Boolean(env.brave);
    return {
        isAndroid,
        isElectron,
        hasMeshChatXAndroid,
        isBrave,
        isSecureContext: Boolean(env.isSecureContext),
        userAgent: ua,
    };
}

function detectSerial(env: Record<string, any>, platform: CapabilityPlatform): TransportCapability {
    const hasNative = Boolean(env.navigator?.serial);
    const hasUsbPolyfillTarget = Boolean(env.navigator?.usb);
    const hasPolyfillModule = Boolean(env.serial);
    const hasNativeFlasher =
        Boolean(env.MeshChatXAndroid) &&
        typeof env.MeshChatXAndroid.hasNativeRNodeFlasher === "function" &&
        Boolean(env.MeshChatXAndroid.hasNativeRNodeFlasher());

    if (hasNativeFlasher) {
        return {
            available: true,
            kind: "android-native-activity",
            polyfilled: false,
            reason: null,
        };
    }
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

function detectBluetooth(env: Record<string, any>, platform: CapabilityPlatform): TransportCapability {
    const hasNative = Boolean(env.navigator?.bluetooth);
    if (hasNative) {
        return {
            available: true,
            kind: "web-bluetooth",
            reason: null,
        };
    }
    if (!platform.isSecureContext) {
        return {
            available: false,
            kind: "none",
            reason: "insecure_context",
        };
    }
    if (platform.hasMeshChatXAndroid) {
        const bridge = env.MeshChatXAndroid;
        const hasPerms =
            typeof bridge?.hasBluetoothPermissions === "function" ? Boolean(bridge.hasBluetoothPermissions()) : false;
        return {
            // WebView still has no Web Bluetooth GATT. Permissions matter for
            // mesh RNode BLE and OS pairing. Keep transport disabled for flash
            // selection, but surface a clearer reason + actions.
            available: false,
            kind: "android-bridge",
            reason: hasPerms ? "android_bridge_no_web_bluetooth" : "android_bluetooth_permission_required",
        };
    }
    // Brave ships Chromium but disables Web Bluetooth until the flag is on.
    // navigator.bluetooth is missing in that state, which looks like "unsupported".
    if (platform.isBrave) {
        return {
            available: false,
            kind: "none",
            reason: "brave_flag_disabled",
        };
    }
    return {
        available: false,
        kind: "none",
        reason: "browser_unsupported",
    };
}

function detectWifi(): TransportCapability {
    return {
        available: true,
        kind: "http",
        reason: null,
    };
}

/** Inspect the environment and return a capabilities snapshot. */
export function detectCapabilities(overrides: DetectCapabilitiesOverrides = {}): CapabilitiesSnapshot {
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
export function pickDefaultTransport(capabilities: CapabilitiesSnapshot | null | undefined): RNodeTransportName {
    const t = capabilities?.transports ?? ({} as CapabilitiesSnapshot["transports"]);
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
export function transportSuggestionKeys(
    capabilities: CapabilitiesSnapshot | null | undefined,
    transportName: string
): string[] {
    const transport = capabilities?.transports?.[transportName as RNodeTransportName];
    if (!transport || transport.available) {
        return [];
    }
    const platform = capabilities?.platform ?? ({} as CapabilityPlatform);
    const reason = transport.reason ?? "unknown";
    const suggestions = [`tools.rnode_flasher.support.${transportName}.${reason}`];
    if (transportName === TRANSPORT_SERIAL && platform.isAndroid) {
        if (reason === "android_webview_no_serial") {
            suggestions.push("tools.rnode_flasher.support.serial.android_use_chrome");
        }
    }
    if (transportName === TRANSPORT_SERIAL && reason === "android_permission_required") {
        suggestions.push("tools.rnode_flasher.support.serial.android_request_usb");
    }
    if (transportName === TRANSPORT_BLUETOOTH && !platform.isSecureContext) {
        suggestions.push("tools.rnode_flasher.support.bluetooth.requires_https");
    }
    if (transportName === TRANSPORT_BLUETOOTH && reason === "brave_flag_disabled") {
        suggestions.push("tools.rnode_flasher.support.bluetooth.brave_enable_flag");
        suggestions.push("tools.rnode_flasher.support.bluetooth.brave_recheck");
    }
    if (transportName === TRANSPORT_BLUETOOTH && reason === "browser_unsupported") {
        suggestions.push("tools.rnode_flasher.support.bluetooth.chromium_linux_hint");
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
