// SPDX-License-Identifier: 0BSD

import { STORAGE_KEYS } from "../constants.js";

/**
 * Local-only relay chat preferences: the client-side ignore list and custom
 * highlight words. Both live under a per-identity bucket so entries written
 * under one identity never leak into another identity's view.
 *
 * Shape: { [identityKey]: { ignored: [{hash, name}], highlightWords: [str], hideJoinPart: bool } }
 * hash entries hold the lowercase peer identity hash, name entries the nick
 * as a fallback for messages that arrive without a src.
 */

const MAX_IGNORED = 500;
const MAX_WORDS = 200;
const MAX_WORD_LEN = 64;

function readRoot() {
    try {
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEYS.RRC_PREFS) || "{}");
        return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
    } catch {
        return {};
    }
}

function writeRoot(root) {
    try {
        localStorage.setItem(STORAGE_KEYS.RRC_PREFS, JSON.stringify(root));
    } catch (e) {
        console.error("Failed to save relay prefs:", e);
    }
}

function normalizeBucket(bucket) {
    const out = { ignored: [], highlightWords: [], hideJoinPart: false };
    if (!bucket || typeof bucket !== "object" || Array.isArray(bucket)) {
        return out;
    }
    out.hideJoinPart = bucket.hideJoinPart === true;
    if (Array.isArray(bucket.ignored)) {
        for (const entry of bucket.ignored) {
            if (!entry || typeof entry !== "object") {
                continue;
            }
            const hash = typeof entry.hash === "string" ? entry.hash.trim().toLowerCase() : "";
            const name = typeof entry.name === "string" ? entry.name.trim() : "";
            if (hash || name) {
                out.ignored.push({ hash, name });
            }
        }
    }
    if (Array.isArray(bucket.highlightWords)) {
        for (const w of bucket.highlightWords) {
            if (typeof w === "string" && w.trim()) {
                out.highlightWords.push(w.trim());
            }
        }
    }
    return out;
}

export function loadRelayPrefs(identityKey = "_") {
    const key = typeof identityKey === "string" && identityKey ? identityKey : "_";
    return normalizeBucket(readRoot()[key]);
}

export function saveRelayPrefs(identityKey, { ignored, highlightWords, hideJoinPart } = {}) {
    const key = typeof identityKey === "string" && identityKey ? identityKey : "_";
    const root = readRoot();
    const previous = normalizeBucket(root[key]);
    const bucket = normalizeBucket({
        ignored,
        highlightWords,
        hideJoinPart: hideJoinPart === undefined ? previous.hideJoinPart : hideJoinPart,
    });
    bucket.ignored = bucket.ignored.slice(0, MAX_IGNORED);
    bucket.highlightWords = bucket.highlightWords.slice(0, MAX_WORDS).map((w) => w.slice(0, MAX_WORD_LEN));
    root[key] = bucket;
    writeRoot(root);
    return bucket;
}

/**
 * True when a peer message comes from an ignored peer. Only chat kinds are
 * filtered. System, notice, and presence rows always stay visible.
 */
export function isIgnoredRelayMessage(msg, ignoredPeers, ownHash = "") {
    if (!msg || (msg.kind !== "msg" && msg.kind !== "action")) {
        return false;
    }
    const src = typeof msg.src === "string" ? msg.src.toLowerCase() : "";
    if (src && ownHash && src === String(ownHash).toLowerCase()) {
        return false;
    }
    const nick = typeof msg.nick === "string" ? msg.nick.toLowerCase() : "";
    return (ignoredPeers || []).some((p) => {
        if (src && p.hash && p.hash === src) {
            return true;
        }
        return Boolean(nick && p.name && p.name.toLowerCase() === nick);
    });
}

export function relayPrefsEqualIgnored(entry, msg) {
    const src = typeof msg?.src === "string" ? msg.src.toLowerCase() : "";
    const nick = typeof msg?.nick === "string" ? msg.nick.toLowerCase() : "";
    return Boolean((src && entry.hash === src) || (nick && entry.name && entry.name.toLowerCase() === nick));
}
