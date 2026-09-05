// SPDX-License-Identifier: 0BSD

/**
 * Predict whether the multi-session warning toast should fire.
 * Mirrors meshchatx.src.backend.active_sessions.should_warn_multi_session.
 */

function parseIpv4Parts(value) {
    const match = String(value || "").match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
    if (!match) {
        return null;
    }
    const parts = match.slice(1).map((part) => Number(part));
    if (parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
        return null;
    }
    return parts;
}

/**
 * True for loopback, RFC1918, link-local, and IPv6 ULA addresses.
 * Mirrors meshchatx.src.backend.active_sessions.is_loopback_or_lan_ip.
 */
export function isLoopbackOrLanIp(value) {
    let cleaned = String(value || "")
        .trim()
        .toLowerCase();
    if (!cleaned || cleaned === "unknown") {
        return false;
    }
    if (cleaned.startsWith("[") && cleaned.endsWith("]")) {
        cleaned = cleaned.slice(1, -1);
    }
    if (cleaned.includes("%")) {
        cleaned = cleaned.split("%")[0];
    }
    if (cleaned.startsWith("::ffff:")) {
        cleaned = cleaned.slice(7);
    }
    if (cleaned === "::1" || cleaned === "0:0:0:0:0:0:0:1") {
        return true;
    }

    const ipv4 = parseIpv4Parts(cleaned);
    if (ipv4) {
        const [a, b] = ipv4;
        if (a === 127) {
            return true;
        }
        if (a === 10) {
            return true;
        }
        if (a === 192 && b === 168) {
            return true;
        }
        if (a === 172 && b >= 16 && b <= 31) {
            return true;
        }
        if (a === 169 && b === 254) {
            return true;
        }
        return false;
    }

    if (cleaned.startsWith("fe80:")) {
        return true;
    }
    const firstHextet = cleaned.split(":", 1)[0] || "";
    if (/^f[cd][0-9a-f]{0,2}$/.test(firstHextet)) {
        return true;
    }
    return false;
}

/**
 * True when every session IP is loopback or LAN (or the list is empty).
 */
export function sessionsAreLocalOnly(sessions) {
    if (!Array.isArray(sessions)) {
        return false;
    }
    if (sessions.length === 0) {
        return true;
    }
    return sessions.every((row) => isLoopbackOrLanIp(row?.ip));
}

export function shouldWarnMultiSession(count, warningEnabled, sessions) {
    const active = Number(count);
    if (!Number.isFinite(active)) {
        return false;
    }
    if (warningEnabled === false || active < 2) {
        return false;
    }
    if (sessions !== undefined && sessionsAreLocalOnly(sessions)) {
        return false;
    }
    return true;
}

/**
 * Fire at most once per multi-session episode (count rises to 2+).
 * Resets when the count drops below 2 so a later episode can warn again.
 */
export function shouldShowMultiSessionToast(count, warningEnabled, alreadyWarned, sessions) {
    const shouldWarn = shouldWarnMultiSession(count, warningEnabled, sessions);
    if (!shouldWarn) {
        return { show: false, warned: false };
    }
    if (alreadyWarned) {
        return { show: false, warned: true };
    }
    return { show: true, warned: true };
}
