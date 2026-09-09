import { LatencyOptimisedTranslator } from "@browsermt/bergamot-translator";
import { BergamotBacking } from "./translation/BergamotBacking.js";

let translator = null;
let backing = null;

function baseUrl() {
    return (import.meta.env.BASE_URL || "/").replace(/\/?$/, "/");
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
    const res = await fetch(`${baseUrl()}api/v1/translation/packs`);
    if (!res.ok) {
        throw new Error(`Failed to list packs: ${res.status}`);
    }
    return (await res.json()).packs || [];
}

export async function importPack(file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${baseUrl()}api/v1/translation/packs/import`, {
        method: "POST",
        body: form,
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Import failed: ${res.status}`);
    }
    await refreshPacks();
    return res.json();
}

export async function removePack(pair) {
    const res = await fetch(`${baseUrl()}api/v1/translation/packs/${encodeURIComponent(pair)}`, {
        method: "DELETE",
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Remove failed: ${res.status}`);
    }
    await refreshPacks();
    return res.json();
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
