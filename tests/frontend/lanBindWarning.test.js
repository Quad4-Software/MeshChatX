// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
    dismissLanBindNoAuthBanner,
    isLanBindNoAuthBannerDismissed,
    LAN_BIND_NO_AUTH_BANNER_DISMISSED_KEY,
    shouldShowLanBindNoAuthBanner,
} from "@/js/lanBindWarning.js";

describe("shouldShowLanBindNoAuthBanner", () => {
    const lanNoAuth = {
        isElectron: false,
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
        expect(shouldShowLanBindNoAuthBanner({ ...lanNoAuth, isElectron: true })).toBe(false);
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
