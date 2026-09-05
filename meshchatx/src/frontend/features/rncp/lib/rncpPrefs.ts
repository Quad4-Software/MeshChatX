// SPDX-License-Identifier: 0BSD

import { DEFAULT_RNCP_LISTEN_PREFS, RNCP_LISTEN_PREFS_KEY } from "./constants.js";
import type { RncpListenPrefs } from "./types.js";

export function loadRncpListenPrefs(): RncpListenPrefs {
    try {
        const raw = localStorage.getItem(RNCP_LISTEN_PREFS_KEY);
        if (!raw) {
            return { ...DEFAULT_RNCP_LISTEN_PREFS };
        }
        const o = JSON.parse(raw);
        return {
            listenAllowedHashes: typeof o.listenAllowedHashes === "string" ? o.listenAllowedHashes : "",
            listenFetchJail: o.listenFetchJail != null ? String(o.listenFetchJail) : null,
            listenFetchAllowed: typeof o.listenFetchAllowed === "boolean" ? o.listenFetchAllowed : false,
            listenAllowOverwrite: typeof o.listenAllowOverwrite === "boolean" ? o.listenAllowOverwrite : false,
        };
    } catch {
        return { ...DEFAULT_RNCP_LISTEN_PREFS };
    }
}

export function saveRncpListenPrefs(prefs: RncpListenPrefs): void {
    try {
        localStorage.setItem(
            RNCP_LISTEN_PREFS_KEY,
            JSON.stringify({
                listenAllowedHashes: prefs.listenAllowedHashes,
                listenFetchJail: prefs.listenFetchJail,
                listenFetchAllowed: prefs.listenFetchAllowed,
                listenAllowOverwrite: prefs.listenAllowOverwrite,
            })
        );
    } catch {
        // ignore quota and storage exceptions
    }
}
