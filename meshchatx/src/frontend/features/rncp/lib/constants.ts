// SPDX-License-Identifier: 0BSD

import type { RncpListenPrefs } from "./types.js";

export const RNCP_LISTEN_PREFS_KEY = "meshchatx.rncp.listenForm.v1";

export const DEFAULT_RNCP_LISTEN_PREFS: RncpListenPrefs = {
    listenAllowedHashes: "",
    listenFetchJail: null,
    listenFetchAllowed: false,
    listenAllowOverwrite: false,
};
