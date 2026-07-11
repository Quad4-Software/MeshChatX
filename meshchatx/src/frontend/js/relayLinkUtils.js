// SPDX-License-Identifier: 0BSD

/**
 * Offline-friendly relay chat deep links:
 * meshchatx://relay?hub=&room=&name=&aspect=
 * (meshchat://relay is accepted as an alias.)
 */

const RELAY_URI_IN_TEXT_RE = /(?:meshchatx|meshchat):\/\/relay\?[^\s<>]*/gi;
const HUB_HASH_RE = /^[a-fA-F0-9]{32}$/;

export function findRelayUriInContent(text) {
    if (!text || typeof text !== "string") {
        return null;
    }
    const matches = text.match(RELAY_URI_IN_TEXT_RE);
    return matches && matches.length ? matches[0] : null;
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
        const list = await api.get("/api/v1/rrc/hubs");
        hubs = list.data?.hubs || [];
    } catch {
        hubs = [];
    }
    const existing = hubs.find((h) => String(h.hub_hash || "").toLowerCase() === hubHash);
    if (!existing) {
        await api.post("/api/v1/rrc/hubs", {
            hub_hash: hubHash,
            name: parsed.name || undefined,
            dest_name: parsed.aspect || "rrc.hub",
            connect: true,
        });
    } else if (!existing.connected) {
        await api.post(`/api/v1/rrc/hubs/${hubHash}/connect`);
    }
    const room = String(parsed.room || "").trim();
    if (room) {
        await api.post(`/api/v1/rrc/hubs/${hubHash}/rooms`, { room });
    }
    return { hub_hash: hubHash, room };
}
