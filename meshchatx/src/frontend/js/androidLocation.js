// SPDX-License-Identifier: 0BSD

/**
 * Native Android GPS bridge for MeshChatX.
 *
 * The WebView geolocation API depends on Google Play Services fused location
 * which fails on devices without it. This module talks to the
 * MeshChatXAndroid bridge, which queries LocationManager (GPS and network
 * providers) directly.
 *
 * Bridge contract (MainActivity.MeshChatXAndroidBridge):
 *   isLocationPermissionGranted() -> boolean
 *   requestLocationPermission()   -> void, fires 'meshchatx-android-permission'
 *                                    with detail { group: 'location', granted }
 *   getLastKnownLocation()        -> JSON string or null
 *   requestFreshLocation()        -> void, fires 'meshchatx-android-location'
 *                                    with detail { latitude, longitude, ... }
 *                                    or { error: '<code>' }
 */

import { isMeshChatXAndroid } from "./webAudioMicPermission.js";

export const ANDROID_LOCATION_EVENT = "meshchatx-android-location";
export const ANDROID_PERMISSION_EVENT = "meshchatx-android-permission";

export class AndroidLocationError extends Error {
    constructor(code) {
        super(code);
        this.code = code;
    }
}

function bridge(win = globalThis) {
    return win?.MeshChatXAndroid;
}

export function isAndroidLocationSupported(win = globalThis) {
    return isMeshChatXAndroid(win) && typeof bridge(win)?.requestFreshLocation === "function";
}

export function androidLocationPermissionGranted(win = globalThis) {
    try {
        return Boolean(bridge(win)?.isLocationPermissionGranted?.());
    } catch {
        return false;
    }
}

function normalizePosition(raw) {
    if (!raw) return null;
    const loc = typeof raw === "string" ? JSON.parse(raw) : raw;
    const lat = Number(loc?.latitude);
    const lon = Number(loc?.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
    return {
        latitude: lat,
        longitude: lon,
        altitude: Number.isFinite(Number(loc.altitude)) ? Number(loc.altitude) : null,
        speed: Number.isFinite(Number(loc.speed)) ? Number(loc.speed) : null,
        bearing: Number.isFinite(Number(loc.bearing)) ? Number(loc.bearing) : null,
        accuracy: Number.isFinite(Number(loc.accuracy)) ? Number(loc.accuracy) : null,
        time: Number.isFinite(Number(loc.time)) ? Number(loc.time) : null,
    };
}

export function getAndroidLastKnownPosition(win = globalThis) {
    try {
        return normalizePosition(bridge(win)?.getLastKnownLocation?.());
    } catch {
        return null;
    }
}

function waitForLocationEvent(win, timeoutMs) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
            cleanup();
            reject(new AndroidLocationError("timeout"));
        }, timeoutMs);
        const onEvent = (event) => {
            cleanup();
            const detail = event?.detail;
            if (detail?.error) {
                reject(new AndroidLocationError(detail.error));
            } else {
                const pos = normalizePosition(detail);
                if (pos) {
                    resolve(pos);
                } else {
                    reject(new AndroidLocationError("unavailable"));
                }
            }
        };
        const cleanup = () => {
            clearTimeout(timer);
            win.removeEventListener(ANDROID_LOCATION_EVENT, onEvent);
        };
        win.addEventListener(ANDROID_LOCATION_EVENT, onEvent);
        try {
            bridge(win).requestFreshLocation();
        } catch {
            cleanup();
            reject(new AndroidLocationError("unavailable"));
        }
    });
}

function waitForPermissionResult(win, timeoutMs) {
    return new Promise((resolve) => {
        const timer = setTimeout(() => {
            cleanup();
            resolve(androidLocationPermissionGranted(win));
        }, timeoutMs);
        const onEvent = (event) => {
            if (event?.detail?.group !== "location") return;
            cleanup();
            resolve(Boolean(event.detail.granted));
        };
        const cleanup = () => {
            clearTimeout(timer);
            win.removeEventListener(ANDROID_PERMISSION_EVENT, onEvent);
        };
        win.addEventListener(ANDROID_PERMISSION_EVENT, onEvent);
        try {
            bridge(win).requestLocationPermission();
        } catch {
            cleanup();
            resolve(false);
        }
    });
}

/**
 * Resolves to { latitude, longitude, altitude, speed, bearing, accuracy, time }.
 * Requests permission when missing and waits for the user to answer the
 * system dialog. Falls back to the last known fix if a fresh fix times out.
 * Rejects with AndroidLocationError whose code is one of:
 *   unsupported, permission_denied, location_disabled, unavailable, timeout
 */
export async function getAndroidPosition(options = {}) {
    const win = options.window || globalThis;
    const freshTimeoutMs = options.timeoutMs ?? 20000;
    const permissionTimeoutMs = options.permissionTimeoutMs ?? 60000;
    if (!isAndroidLocationSupported(win)) {
        throw new AndroidLocationError("unsupported");
    }
    if (!androidLocationPermissionGranted(win)) {
        const granted = await waitForPermissionResult(win, permissionTimeoutMs);
        if (!granted) {
            throw new AndroidLocationError("permission_denied");
        }
    }
    try {
        return await waitForLocationEvent(win, freshTimeoutMs);
    } catch (err) {
        const cached = getAndroidLastKnownPosition(win);
        if (cached && (err?.code === "timeout" || err?.code === "unavailable")) {
            return cached;
        }
        throw err;
    }
}
