// SPDX-License-Identifier: 0BSD

/**
 * Offline translation service backed by the Bergamot WASM engine.
 *
 * Pack management calls the local backend (/api/v1/translation/packs*).
 * Translation itself runs entirely in the browser through a serialized
 * promise queue so the WASM worker never sees concurrent calls.
 */

import { LatencyOptimisedTranslator, type BergamotTranslateResult } from "@browsermt/bergamot-translator";

import type { ApiClient, ApiRequestConfig } from "./apiClient.js";
import { apiPath } from "./constants.js";
import { BergamotBacking } from "./translation/BergamotBacking.js";

export interface TranslationPack {
    pair: string;
    from: string;
    to: string;
    size: number;
    version?: string;
    [key: string]: unknown;
}

export interface TranslateParams {
    from: string;
    to: string;
    text: string;
    html?: boolean;
    signal?: AbortSignal | null;
}

let translator: LatencyOptimisedTranslator | null = null;
let backing: BergamotBacking | null = null;
let queue: Promise<unknown> = Promise.resolve();

function withTranslator<T>(fn: () => Promise<T>): Promise<T> {
    const next = queue.then(fn);
    queue = next.catch(() => {});
    return next;
}

function apiUrl(path: string): string {
    const base = import.meta.env.BASE_URL || "/";
    const origin = typeof window !== "undefined" && window.location ? window.location.origin : "http://localhost";
    const prefix = `${origin}${base.replace(/\/?$/, "/")}`;
    return `${prefix}${path.replace(/^\//, "")}`;
}

function apiClient(): ApiClient | null {
    if (typeof window !== "undefined" && window.api) {
        return window.api;
    }
    return null;
}

async function apiGet<T>(path: string): Promise<T> {
    const client = apiClient();
    if (client?.get) {
        const res = await client.get(path);
        return res.data as T;
    }
    const res = await fetch(apiUrl(path));
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
}

async function apiPost<T>(path: string, body: unknown, config: ApiRequestConfig = {}): Promise<T> {
    const client = apiClient();
    if (client?.post) {
        const res = await client.post(path, body, config);
        return res.data as T;
    }
    const res = await fetch(apiUrl(path), { method: "POST", body: body as BodyInit });
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
}

async function apiDelete<T>(path: string): Promise<T> {
    const client = apiClient();
    if (client?.delete) {
        const res = await client.delete(path);
        return res.data as T;
    }
    const res = await fetch(apiUrl(path), { method: "DELETE" });
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
}

async function doEnsureTranslator(): Promise<LatencyOptimisedTranslator> {
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

/**
 * Drop the cached translator so a later translate() picks up newly
 * imported packs. Queued behind any in-flight translation.
 */
export async function refreshPacks(): Promise<void> {
    return withTranslator(async () => {
        if (translator) {
            const old = translator;
            translator = null;
            backing = null;
            await old.delete().catch(() => {});
        }
    });
}

export async function listPacks(): Promise<TranslationPack[]> {
    const data = await apiGet<{ packs?: TranslationPack[] }>(apiPath("/translation/packs"));
    return data.packs || [];
}

export async function importPack(file: File | Blob): Promise<unknown> {
    const form = new FormData();
    form.append("file", file);
    const data = await apiPost(apiPath("/translation/packs/import"), form);
    await refreshPacks();
    return data;
}

export async function removePack(pair: string): Promise<unknown> {
    const data = await apiDelete(apiPath(`/translation/packs/${encodeURIComponent(pair)}`));
    await refreshPacks();
    return data;
}

export async function translate(params: TranslateParams): Promise<BergamotTranslateResult> {
    const { from, to, text, html = false, signal = null } = params;
    if (!text || !from || !to) {
        throw new Error("Missing source, target, or text");
    }
    if (signal?.aborted) {
        throw new Error("Translation cancelled");
    }
    return withTranslator(async () => {
        const t = await doEnsureTranslator();
        const request = { from, to, text, html };
        const options: { signal?: AbortSignal } = {};
        if (signal) {
            options.signal = signal;
        }
        return t.translate(request, options);
    });
}
