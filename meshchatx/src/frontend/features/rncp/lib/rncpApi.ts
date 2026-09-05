// SPDX-License-Identifier: 0BSD

import type { RncpStatus } from "./types.js";

type WindowApi = {
    get: (url: string, config?: { params?: Record<string, unknown> }) => Promise<{ data?: unknown }>;
    post: (url: string, body?: unknown) => Promise<{ data?: unknown }>;
};

function getApi(): WindowApi {
    const api = (window as unknown as { api?: WindowApi }).api;
    if (!api) {
        throw new Error("window.api is not available");
    }
    return api;
}

export async function fetchRncpStatus(): Promise<RncpStatus> {
    const res = await getApi().get("/api/v1/rncp/status");
    return (res.data || {}) as RncpStatus;
}

export async function sendRncpFile(payload: {
    destination_hash: string;
    file_path: string;
    timeout?: number;
    no_compress?: boolean;
}): Promise<{ transfer_id: string; file_path?: string }> {
    const res = await getApi().post("/api/v1/rncp/send", payload);
    return (res.data || {}) as { transfer_id: string; file_path?: string };
}

export async function cancelRncpTransfer(transfer_id?: string): Promise<void> {
    await getApi().post("/api/v1/rncp/cancel", {
        transfer_id: transfer_id || undefined,
    });
}

export async function fetchRncpFile(payload: {
    destination_hash: string;
    file_path: string;
    timeout?: number;
    save_path?: string | null;
    allow_overwrite?: boolean;
}): Promise<{ file_path?: string; transfer_id?: string }> {
    const res = await getApi().post("/api/v1/rncp/fetch", payload);
    return (res.data || {}) as { file_path?: string; transfer_id?: string };
}

export async function startRncpListen(payload: {
    allowed_hashes: string[];
    fetch_allowed?: boolean;
    fetch_jail?: string | null;
    allow_overwrite?: boolean;
}): Promise<{ destination_hash: string; message: string }> {
    const res = await getApi().post("/api/v1/rncp/listen", payload);
    return (res.data || {}) as { destination_hash: string; message: string };
}

export async function stopRncpListen(): Promise<void> {
    await getApi().post("/api/v1/rncp/stop");
}
