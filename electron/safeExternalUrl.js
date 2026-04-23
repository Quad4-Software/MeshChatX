"use strict";

/**
 * Returns a normalized http(s) or mailto URL suitable for shell.openExternal,
 * or null if the input must not be handed to the OS shell.
 * @param {unknown} raw
 * @returns {string|null}
 */
function normalizeExternalUrlForOpen(raw) {
    if (typeof raw !== "string") {
        return null;
    }
    const s = raw.trim();
    if (!s) {
        return null;
    }
    let u;
    try {
        u = new URL(s);
    } catch {
        return null;
    }
    const p = u.protocol;
    if (p === "http:" || p === "https:") {
        return u.href;
    }
    if (p === "mailto:") {
        return u.href;
    }
    return null;
}

module.exports = {
    normalizeExternalUrlForOpen,
};
