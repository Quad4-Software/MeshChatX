// SPDX-License-Identifier: 0BSD

/**
 * Browser-only LAN bind warning. Electron and Android bind locally and
 * never show this. Headless LAN binds keep running. The UI warns instead.
 */

export const LAN_BIND_NO_AUTH_BANNER_DISMISSED_KEY = "meshchatx_lan_bind_no_auth_banner_dismissed";

export function isLanBindNoAuthBannerDismissed() {
    try {
        return localStorage.getItem(LAN_BIND_NO_AUTH_BANNER_DISMISSED_KEY) === "1";
    } catch {
        return false;
    }
}

export function dismissLanBindNoAuthBanner() {
    try {
        localStorage.setItem(LAN_BIND_NO_AUTH_BANNER_DISMISSED_KEY, "1");
    } catch {
        /* ignore storage failures */
    }
}

export function shouldShowLanBindNoAuthBanner({
    isElectron = false,
    isAndroid = false,
    authEnabled = false,
    isLoopbackBind = true,
    routeName = "",
    dismissed = false,
}: any = {}) {
    if (dismissed || isLanBindNoAuthBannerDismissed()) {
        return false;
    }
    if (isElectron || isAndroid) {
        return false;
    }
    if (routeName === "auth") {
        return false;
    }
    if (authEnabled) {
        return false;
    }
    return isLoopbackBind === false;
}
