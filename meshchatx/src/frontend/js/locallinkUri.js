// SPDX-License-Identifier: 0BSD

/**
 * WIFI: QR payload codec for the Nearby local-link feature.
 *
 * Format: WIFI:T:<security>;S:<ssid>;P:<pass>;H:<hidden>;;
 * Field values escape \ ; , : " with a backslash.
 * Parsing is strict: unknown trailing junk, missing S, or oversized
 * fields return null so a hostile QR cannot drive a join.
 */

const WIFI_PREFIX = "WIFI:";
const MAX_SSID_LEN = 32;
const MAX_PSK_LEN = 63;
const SECURITY_TYPES = new Set(["WPA", "WPA2", "WPA3", "WEP", "nopass"]);

function escapeField(value) {
    return String(value).replace(/([\\;,"':])/g, "\\$1");
}

function unescapeField(value) {
    let out = "";
    let escaped = false;
    for (const ch of value) {
        if (escaped) {
            out += ch;
            escaped = false;
        } else if (ch === "\\") {
            escaped = true;
        } else {
            out += ch;
        }
    }
    if (escaped) {
        return null;
    }
    return out;
}

function splitFields(body) {
    const fields = [];
    let current = "";
    let escaped = false;
    for (const ch of body) {
        if (escaped) {
            current += "\\" + ch;
            escaped = false;
        } else if (ch === "\\") {
            escaped = true;
        } else if (ch === ";") {
            fields.push(current);
            current = "";
        } else {
            current += ch;
        }
    }
    if (escaped) {
        current += "\\";
    }
    fields.push(current);
    return fields;
}

export function buildWifiQrPayload({ ssid, passphrase = "", security = "WPA", hidden = false }) {
    if (typeof ssid !== "string" || ssid.length === 0 || ssid.length > MAX_SSID_LEN) {
        return null;
    }
    if (passphrase && (passphrase.length < 8 || passphrase.length > MAX_PSK_LEN)) {
        return null;
    }
    const sec = security === "nopass" || !passphrase ? "nopass" : security;
    return (
        WIFI_PREFIX +
        `T:${escapeField(sec)};` +
        `S:${escapeField(ssid)};` +
        (passphrase ? `P:${escapeField(passphrase)};` : "") +
        (hidden ? "H:true;" : "") +
        ";"
    );
}

export function parseWifiQrPayload(text) {
    if (typeof text !== "string") {
        return null;
    }
    const trimmed = text.trim();
    if (!trimmed.toUpperCase().startsWith(WIFI_PREFIX)) {
        return null;
    }
    const body = trimmed.slice(WIFI_PREFIX.length);
    const fields = splitFields(body);
    const out = { security: "nopass", ssid: null, passphrase: null, hidden: false };
    for (const field of fields) {
        if (field === "") {
            continue;
        }
        const sep = field.indexOf(":");
        if (sep < 0) {
            return null;
        }
        const key = field.slice(0, sep).toUpperCase();
        const value = unescapeField(field.slice(sep + 1));
        if (value === null) {
            return null;
        }
        if (key === "T") {
            const normalized = value === "nopass" ? "nopass" : value.toUpperCase();
            if (!SECURITY_TYPES.has(normalized)) {
                return null;
            }
            out.security = normalized === "nopass" ? "nopass" : normalized;
        } else if (key === "S") {
            out.ssid = value;
        } else if (key === "P") {
            out.passphrase = value;
        } else if (key === "H") {
            out.hidden = value.toLowerCase() === "true";
        }
        // Unknown keys are ignored per the format spec.
    }
    if (!out.ssid || out.ssid.length > MAX_SSID_LEN) {
        return null;
    }
    if (out.passphrase && out.passphrase.length > MAX_PSK_LEN) {
        return null;
    }
    return out;
}
