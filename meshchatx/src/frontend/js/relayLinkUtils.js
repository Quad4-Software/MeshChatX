// SPDX-License-Identifier: 0BSD

/**
 * Offline-friendly relay chat deep links:
 * meshchatx://relay?hub=&room=&name=&aspect=
 * (meshchat://relay is accepted as an alias.)
 * rrc://<hub_hash>/<room> is the short paste-friendly form.
 */

import { apiPath } from "./constants.js";

const RELAY_URI_IN_TEXT_RE = /(?:meshchatx|meshchat):\/\/relay\?[^\s<>]*/gi;
const RRC_URI_IN_TEXT_RE = /rrc:\/\/[^\s<>]+/gi;
const HUB_HASH_RE = /^[a-fA-F0-9]{32}$/;

function trimUriTrailingPunctuation(uri) {
    let core = uri;
    // Quotes matter: a pasted link inside quotes would otherwise join a room
    // whose name ends in a stray quote character.
    while (core.length > 0 && /[.,!?;:)\]"']/.test(core.at(-1))) {
        core = core.slice(0, -1);
    }
    return core;
}

export function findRelayUriInContent(text) {
    if (!text || typeof text !== "string") {
        return null;
    }
    const meshMatches = text.match(RELAY_URI_IN_TEXT_RE);
    if (meshMatches && meshMatches.length) {
        return meshMatches[0];
    }
    const rrcMatches = text.match(RRC_URI_IN_TEXT_RE);
    if (rrcMatches && rrcMatches.length) {
        const candidate = trimUriTrailingPunctuation(rrcMatches[0]);
        if (parseRrcRelayUri(candidate)) {
            return candidate;
        }
    }
    return null;
}

export function parseMeshchatRelayUri(uri) {
    if (!uri || typeof uri !== "string") {
        return null;
    }
    const s = uri.trim();
    if (!/^(meshchatx|meshchat):\/\/relay\b/i.test(s)) {
        return null;
    }
    try {
        const u = new URL(s);
        const hub = String(u.searchParams.get("hub") || "")
            .trim()
            .toLowerCase();
        if (!HUB_HASH_RE.test(hub)) {
            return null;
        }
        const room = String(u.searchParams.get("room") || "").trim();
        const name = String(u.searchParams.get("name") || "").trim();
        const aspect = String(u.searchParams.get("aspect") || u.searchParams.get("dest_name") || "")
            .trim()
            .slice(0, 64);
        return {
            hub,
            room: room || "",
            name: name || "",
            aspect: aspect || "rrc.hub",
            raw: s,
        };
    } catch {
        return null;
    }
}

/**
 * Parse the short paste form rrc://<hub_hash>/<room>.
 * Room names are URL-decoded. Names with slashes stay ambiguous and only the
 * first path segment boundary separates hub from room.
 */
export function parseRrcRelayUri(uri) {
    if (!uri || typeof uri !== "string") {
        return null;
    }
    const s = uri.trim();
    if (!/^rrc:\/\//i.test(s)) {
        return null;
    }
    try {
        const u = new URL(s);
        const hub = String(u.host || "")
            .trim()
            .toLowerCase();
        if (!HUB_HASH_RE.test(hub)) {
            return null;
        }
        let room = "";
        try {
            room = decodeURIComponent(u.pathname.replace(/^\/+/, "")).trim();
        } catch {
            return null;
        }
        if (!room) {
            return null;
        }
        return {
            hub,
            room,
            name: "",
            aspect: "rrc.hub",
            raw: s,
        };
    } catch {
        return null;
    }
}

/**
 * Accepts every supported relay URI form and returns the shared
 * { hub, room, name, aspect, raw } shape.
 */
export function parseRelayUri(uri) {
    if (uri && /^rrc:\/\//i.test(String(uri).trim())) {
        return parseRrcRelayUri(uri);
    }
    return parseMeshchatRelayUri(uri);
}

export function buildMeshchatRelayUri({ hub, room = "", name = "", aspect = "" } = {}) {
    const h = String(hub || "")
        .trim()
        .toLowerCase();
    if (!HUB_HASH_RE.test(h)) {
        return null;
    }
    const parts = [`hub=${encodeURIComponent(h)}`];
    const r = String(room || "").trim();
    if (r) {
        parts.push(`room=${encodeURIComponent(r)}`);
    }
    const n = String(name || "").trim();
    if (n) {
        parts.push(`name=${encodeURIComponent(n)}`);
    }
    const a = String(aspect || "").trim();
    if (a && a !== "rrc.hub") {
        parts.push(`aspect=${encodeURIComponent(a)}`);
    }
    return `meshchatx://relay?${parts.join("&")}`;
}

export function buildRelayShareMessage({ hub, room = "", name = "", aspect = "" } = {}) {
    const uri = buildMeshchatRelayUri({ hub, room, name, aspect });
    if (!uri) {
        return null;
    }
    if (room) {
        return `MeshChatX relay room: ${uri}`;
    }
    return `MeshChatX relay: ${uri}`;
}

/**
 * Add (or reuse) a client hub from a parsed relay URI and optionally join a room.
 * Returns { hub_hash, room } on success.
 */
export async function applyRelayShareLink(parsed, { api = typeof window !== "undefined" ? window.api : null } = {}) {
    if (!parsed?.hub || !api) {
        throw new Error("invalid relay share");
    }
    const hubHash = parsed.hub;
    let hubs = [];
    try {
        const list = await api.get(apiPath("/rrc/hubs"));
        hubs = list.data?.hubs || [];
    } catch {
        hubs = [];
    }
    const existing = hubs.find((h) => String(h.hub_hash || "").toLowerCase() === hubHash);
    if (!existing) {
        await api.post(apiPath("/rrc/hubs"), {
            hub_hash: hubHash,
            name: parsed.name || undefined,
            dest_name: parsed.aspect || "rrc.hub",
            connect: true,
        });
    } else if (!existing.connected) {
        await api.post(apiPath(`/rrc/hubs/${hubHash}/connect`));
    }
    const room = String(parsed.room || "").trim();
    if (room) {
        await api.post(apiPath(`/rrc/hubs/${hubHash}/rooms`), { room });
    }
    return { hub_hash: hubHash, room };
}
