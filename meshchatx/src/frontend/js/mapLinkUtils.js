// SPDX-License-Identifier: 0BSD

/**
 * Offline-friendly map deep links: meshchatx://map?lat=&lon=&z=&layers=&label=
 * (meshchat://map is accepted as an alias.)
 */

const MAP_URI_IN_TEXT_RE = /(?:meshchatx|meshchat):\/\/map\?[^\s<>]*/gi;

export function findMapUriInContent(text) {
    if (!text || typeof text !== "string") {
        return null;
    }
    const matches = text.match(MAP_URI_IN_TEXT_RE);
    return matches && matches.length ? matches[0] : null;
}

export function parseMeshchatMapUri(uri) {
    if (!uri || typeof uri !== "string") {
        return null;
    }
    const s = uri.trim();
    if (!/^(meshchatx|meshchat):\/\/map\b/i.test(s)) {
        return null;
    }
    try {
        const u = new URL(s);
        const lat = parseFloat(u.searchParams.get("lat") ?? "");
        const lon = parseFloat(u.searchParams.get("lon") ?? "");
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
            return null;
        }
        const zRaw = u.searchParams.get("z") ?? u.searchParams.get("zoom") ?? "10";
        let zoom = Math.round(parseFloat(zRaw));
        if (!Number.isFinite(zoom)) {
            zoom = 10;
        }
        zoom = Math.max(0, Math.min(22, zoom));
        const layers = (u.searchParams.get("layers") || "").trim();
        const label = (u.searchParams.get("label") || "").trim();
        return { lat, lon, zoom, layers, label, raw: s };
    } catch {
        return null;
    }
}

export function buildMeshchatMapUri({ lat, lon, zoom, layers = "", label = "" }) {
    const z = Math.round(Number(zoom));
    const parts = [`lat=${encodeURIComponent(lat)}`, `lon=${encodeURIComponent(lon)}`, `z=${encodeURIComponent(z)}`];
    if (layers) {
        parts.push(`layers=${encodeURIComponent(layers)}`);
    }
    if (label) {
        parts.push(`label=${encodeURIComponent(label)}`);
    }
    return `meshchatx://map?${parts.join("&")}`;
}

export function buildWebHashMapUrl({ lat, lon, zoom, layers = "", label = "" }) {
    const q = new URLSearchParams();
    q.set("lat", String(lat));
    q.set("lon", String(lon));
    q.set("zoom", String(Math.round(Number(zoom))));
    if (layers) {
        q.set("layers", layers);
    }
    if (label) {
        q.set("label", label);
    }
    const base = typeof window !== "undefined" ? `${window.location.origin}${window.location.pathname}` : "";
    return `${base}#/map?${q.toString()}`;
}

export function mapLinkKindFromMessage(content, parsed) {
    if (content && typeof content === "string" && /MeshChatX\s+map\s+ping/i.test(content)) {
        return "ping";
    }
    if (parsed?.label && /^ping$/i.test(parsed.label)) {
        return "ping";
    }
    return "view";
}
