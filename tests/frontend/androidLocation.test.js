// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
    AndroidLocationError,
    ANDROID_LOCATION_EVENT,
    ANDROID_PERMISSION_EVENT,
    androidLocationPermissionGranted,
    getAndroidLastKnownPosition,
    getAndroidPosition,
    isAndroidLocationSupported,
} from "../../meshchatx/src/frontend/js/androidLocation.js";

function makeWin(overrides = {}) {
    const listeners = new Map();
    const win = {
        MeshChatXAndroid: {
            getPlatform: () => "android",
            isLocationPermissionGranted: () => true,
            requestLocationPermission: vi.fn(),
            getLastKnownLocation: vi.fn(() => null),
            requestFreshLocation: vi.fn(),
        },
        addEventListener: (name, fn) => listeners.set(name, fn),
        removeEventListener: (name, fn) => {
            if (listeners.get(name) === fn) listeners.delete(name);
        },
        dispatch: (name, detail) => listeners.get(name)?.({ detail }),
        ...overrides,
    };
    return win;
}

describe("androidLocation", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });
    afterEach(() => {
        vi.useRealTimers();
    });

    it("reports unsupported when the bridge or method is missing", () => {
        expect(isAndroidLocationSupported({})).toBe(false);
        expect(isAndroidLocationSupported(makeWin())).toBe(true);
    });

    it("reads the permission state from the bridge", () => {
        const win = makeWin();
        expect(androidLocationPermissionGranted(win)).toBe(true);
        win.MeshChatXAndroid.isLocationPermissionGranted = () => false;
        expect(androidLocationPermissionGranted(win)).toBe(false);
    });

    it("parses the last known location JSON", () => {
        const win = makeWin();
        win.MeshChatXAndroid.getLastKnownLocation = () =>
            JSON.stringify({ latitude: 12.5, longitude: -45.25, accuracy: 8, time: 5000 });
        expect(getAndroidLastKnownPosition(win)).toEqual({
            latitude: 12.5,
            longitude: -45.25,
            altitude: null,
            speed: null,
            bearing: null,
            accuracy: 8,
            time: 5000,
        });
        win.MeshChatXAndroid.getLastKnownLocation = () => "not json";
        expect(getAndroidLastKnownPosition(win)).toBeNull();
    });

    it("rejects with unsupported when the bridge method is missing", async () => {
        await expect(getAndroidPosition({ window: {} })).rejects.toMatchObject({
            code: "unsupported",
        });
    });

    it("resolves with a fresh fix event", async () => {
        const win = makeWin();
        const promise = getAndroidPosition({ window: win });
        expect(win.MeshChatXAndroid.requestFreshLocation).toHaveBeenCalled();
        win.dispatch(ANDROID_LOCATION_EVENT, { latitude: 1, longitude: 2 });
        await expect(promise).resolves.toMatchObject({ latitude: 1, longitude: 2 });
    });

    it("requests permission first and retries when granted", async () => {
        const win = makeWin();
        win.MeshChatXAndroid.isLocationPermissionGranted = () => false;
        const promise = getAndroidPosition({ window: win });
        await Promise.resolve();
        expect(win.MeshChatXAndroid.requestLocationPermission).toHaveBeenCalled();
        win.dispatch(ANDROID_PERMISSION_EVENT, { group: "location", granted: true });
        await Promise.resolve();
        win.dispatch(ANDROID_LOCATION_EVENT, { latitude: 3, longitude: 4 });
        await expect(promise).resolves.toMatchObject({ latitude: 3, longitude: 4 });
    });

    it("rejects with permission_denied when the user refuses", async () => {
        const win = makeWin();
        win.MeshChatXAndroid.isLocationPermissionGranted = () => false;
        const promise = getAndroidPosition({ window: win });
        await Promise.resolve();
        win.dispatch(ANDROID_PERMISSION_EVENT, { group: "location", granted: false });
        await expect(promise).rejects.toBeInstanceOf(AndroidLocationError);
        await expect(promise).rejects.toMatchObject({ code: "permission_denied" });
    });

    it("falls back to the last known fix when a fresh fix fails", async () => {
        const win = makeWin();
        win.MeshChatXAndroid.getLastKnownLocation = () => JSON.stringify({ latitude: 9, longitude: 9 });
        const promise = getAndroidPosition({ window: win });
        win.dispatch(ANDROID_LOCATION_EVENT, { error: "unavailable" });
        await expect(promise).resolves.toMatchObject({ latitude: 9, longitude: 9 });
    });

    it("propagates location_disabled instead of using the cache", async () => {
        const win = makeWin();
        win.MeshChatXAndroid.getLastKnownLocation = () => JSON.stringify({ latitude: 9, longitude: 9 });
        const promise = getAndroidPosition({ window: win });
        win.dispatch(ANDROID_LOCATION_EVENT, { error: "location_disabled" });
        await expect(promise).rejects.toMatchObject({ code: "location_disabled" });
    });
});
