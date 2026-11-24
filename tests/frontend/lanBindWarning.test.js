// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
    dismissInsecureRemoteAccessBanner,
    dismissLanBindNoAuthBanner,
    INSECURE_REMOTE_ACCESS_DISMISSED_KEY,
    isInsecureRemoteAccessBannerDismissed,
    isLanBindNoAuthBannerDismissed,
    LAN_BIND_NO_AUTH_BANNER_DISMISSED_KEY,
    shouldShowInsecureRemoteAccessBanner,
    shouldShowLanBindNoAuthBanner,
} from "@/js/lanBindWarning.js";

describe("shouldShowLanBindNoAuthBanner", () => {
    const lanNoAuth = {
        isDesktop: false,
        isAndroid: false,
        authEnabled: false,
        isLoopbackBind: false,
        routeName: "messages",
        dismissed: false,
    };

    beforeEach(() => {
        localStorage.removeItem(LAN_BIND_NO_AUTH_BANNER_DISMISSED_KEY);
    });

    afterEach(() => {
        localStorage.removeItem(LAN_BIND_NO_AUTH_BANNER_DISMISSED_KEY);
    });

    it("shows for browser LAN bind without auth", () => {
        expect(shouldShowLanBindNoAuthBanner(lanNoAuth)).toBe(true);
    });

    it("hides on electron, android, loopback, auth, or auth route", () => {
        expect(shouldShowLanBindNoAuthBanner({ ...lanNoAuth, isDesktop: true })).toBe(false);
        expect(shouldShowLanBindNoAuthBanner({ ...lanNoAuth, isAndroid: true })).toBe(false);
        expect(shouldShowLanBindNoAuthBanner({ ...lanNoAuth, isLoopbackBind: true })).toBe(false);
        expect(shouldShowLanBindNoAuthBanner({ ...lanNoAuth, authEnabled: true })).toBe(false);
        expect(shouldShowLanBindNoAuthBanner({ ...lanNoAuth, routeName: "auth" })).toBe(false);
    });

    it("stays hidden after dismiss is persisted", () => {
        dismissLanBindNoAuthBanner();
        expect(isLanBindNoAuthBannerDismissed()).toBe(true);
        expect(shouldShowLanBindNoAuthBanner(lanNoAuth)).toBe(false);
        expect(shouldShowLanBindNoAuthBanner({ ...lanNoAuth, dismissed: true })).toBe(false);
    });
});

describe("shouldShowInsecureRemoteAccessBanner", () => {
    const flagged = {
        appInfo: { insecure_remote_access: true },
        routeName: "messages",
        dismissed: false,
    };

    beforeEach(() => {
        sessionStorage.clear();
    });

    afterEach(() => {
        sessionStorage.clear();
    });

    it("shows when the backend flags insecure remote access", () => {
        expect(shouldShowInsecureRemoteAccessBanner(flagged)).toBe(true);
    });

    it("hides when the flag is false, missing, or on the auth route", () => {
        expect(
            shouldShowInsecureRemoteAccessBanner({
                ...flagged,
                appInfo: { insecure_remote_access: false },
            }),
        ).toBe(false);
        expect(shouldShowInsecureRemoteAccessBanner({ ...flagged, appInfo: {} })).toBe(false);
        expect(shouldShowInsecureRemoteAccessBanner({ ...flagged, appInfo: null })).toBe(false);
        expect(shouldShowInsecureRemoteAccessBanner({ ...flagged, routeName: "auth" })).toBe(false);
        expect(shouldShowInsecureRemoteAccessBanner({ ...flagged, dismissed: true })).toBe(false);
    });

    it("dismiss persists only for the session via sessionStorage", () => {
        dismissInsecureRemoteAccessBanner();
        expect(isInsecureRemoteAccessBannerDismissed()).toBe(true);
        expect(sessionStorage.getItem(INSECURE_REMOTE_ACCESS_DISMISSED_KEY)).toBe("1");
        expect(localStorage.getItem(INSECURE_REMOTE_ACCESS_DISMISSED_KEY)).toBeNull();
        expect(shouldShowInsecureRemoteAccessBanner(flagged)).toBe(false);
        sessionStorage.clear();
        expect(shouldShowInsecureRemoteAccessBanner(flagged)).toBe(true);
    });
});
