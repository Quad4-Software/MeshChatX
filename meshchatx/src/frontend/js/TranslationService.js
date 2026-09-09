import { LatencyOptimisedTranslator } from "@browsermt/bergamot-translator";
import { BergamotBacking } from "./translation/BergamotBacking.js";

let translator = null;
let backing = null;

function apiUrl(path) {
    const base = import.meta.env.BASE_URL || "/";
    const origin = typeof window !== "undefined" && window.location ? window.location.origin : "http://localhost";
    const prefix = `${origin}${base.replace(/\/?$/, "/")}`;
    return `${prefix}${path.replace(/^\//, "")}`;
}

function apiClient() {
    if (typeof window !== "undefined" && window.api) {
        return window.api;
    }
    return null;
}

async function apiGet(path) {
    const client = apiClient();
    if (client?.get) {
        const res = await client.get(apiUrl(path));
        return res.data;
    }
    const res = await fetch(apiUrl(path));
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
}

async function apiPost(path, body, config = {}) {
    const client = apiClient();
    if (client?.post) {
        const res = await client.post(apiUrl(path), body, config);
        return res.data;
    }
    const res = await fetch(apiUrl(path), { method: "POST", body });
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
}

async function apiDelete(path) {
    const client = apiClient();
    if (client?.delete) {
        const res = await client.delete(apiUrl(path));
        return res.data;
    }
    const res = await fetch(apiUrl(path), { method: "DELETE" });
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
}

async function ensureTranslator() {
    if (translator && backing) {
        return translator;
    }
    if (translator) {
        await translator.delete().catch(() => {});
    }
    backing = new BergamotBacking();
    translator = new LatencyOptimisedTranslator({}, backing);
    return translator;
}

export async function refreshPacks() {
    if (translator) {
        const old = translator;
        translator = null;
        await old.delete().catch(() => {});
    }
    backing = null;
}

export async function listPacks() {
    const data = await apiGet("/api/v1/translation/packs");
    return data.packs || [];
}

export async function importPack(file) {
    const form = new FormData();
    form.append("file", file);
    const data = await apiPost("/api/v1/translation/packs/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
    });
    await refreshPacks();
    return data;
}

export async function removePack(pair) {
    const data = await apiDelete(`/api/v1/translation/packs/${encodeURIComponent(pair)}`);
    await refreshPacks();
    return data;
}

export async function translate({ from, to, text, html = false, signal = null }) {
    if (!text || !from || !to) {
        throw new Error("Missing source, target, or text");
    }
    const t = await ensureTranslator();
    const request = { from, to, text, html };
    const options = {};
    if (signal) {
        options.signal = signal;
    }
    return t.translate(request, options);
}
