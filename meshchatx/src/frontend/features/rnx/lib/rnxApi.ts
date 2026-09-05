// SPDX-License-Identifier: 0BSD

import type {
    RnxExecuteForm,
    RnxExecutePayload,
    RnxListenForm,
    RnxListenPayload,
    RnxSession,
} from "./types.js";

/**
 * Build execute or interactive session payload from form values
 */
export function buildRnxExecutePayload(form: RnxExecuteForm): RnxExecutePayload {
    const interactive = !!form.interactive;
    const formatLimit = (value: string | number | undefined): string | undefined => {
        if (value === undefined || value === null) return undefined;
        const s = String(value).trim();
        return s.length > 0 ? s : undefined;
    };

    return {
        name: form.name.trim() || undefined,
        mode: interactive ? "interactive" : "execute",
        destination: form.destination.trim(),
        remote_command: interactive ? undefined : form.command.trim() || undefined,
        config_path: form.config_path.trim() || undefined,
        mirror: !!form.mirror,
        no_id: !!form.no_id,
        detailed: !!form.detailed,
        timeout: formatLimit(form.timeout),
        result_timeout: formatLimit(form.result_timeout),
        stdout_limit: formatLimit(form.stdout_limit),
        stderr_limit: formatLimit(form.stderr_limit),
        autostart: true,
    };
}

/**
 * Build listen session payload from form values
 */
export function buildRnxListenPayload(form: RnxListenForm): RnxListenPayload {
    return {
        name: form.name.trim() || undefined,
        mode: "listen",
        allowed_hashes: form.allowed_hashes_text
            .split("\n")
            .map((value) => value.trim())
            .filter((value) => value.length > 0),
        config_path: form.config_path.trim() || undefined,
        no_auth: !!form.no_auth,
        autostart: true,
    };
}

/**
 * Fetch all RNX sessions
 */
export async function fetchRnxSessions(): Promise<RnxSession[]> {
    const response = await window.api.get("/api/v1/rnx/sessions");
    const data = response.data as { sessions?: RnxSession[] } | undefined;
    return Array.isArray(data?.sessions) ? data.sessions : [];
}

/**
 * Create a new RNX session
 */
export async function createRnxSession(
    payload: RnxExecutePayload | RnxListenPayload
): Promise<RnxSession | null> {
    const response = await window.api.post("/api/v1/rnx/sessions", payload);
    const data = response.data as { session?: RnxSession } | undefined;
    return data?.session || null;
}

/**
 * Start an RNX session
 */
export async function startRnxSession(sessionId: string): Promise<void> {
    await window.api.post(`/api/v1/rnx/sessions/${sessionId}/start`, {});
}

/**
 * Stop an RNX session
 */
export async function stopRnxSession(sessionId: string): Promise<void> {
    await window.api.post(`/api/v1/rnx/sessions/${sessionId}/stop`, {});
}

/**
 * Remove an RNX session
 */
export async function removeRnxSession(sessionId: string): Promise<void> {
    await window.api.delete(`/api/v1/rnx/sessions/${sessionId}`);
}

/**
 * Clear terminal output for an RNX session
 */
export async function clearRnxSessionOutput(sessionId: string): Promise<RnxSession | null> {
    const response = await window.api.post(`/api/v1/rnx/sessions/${sessionId}/clear`, {});
    const data = response.data as { session?: RnxSession } | undefined;
    return data?.session || null;
}

/**
 * Send interactive text input to an RNX session
 */
export async function sendRnxSessionInput(sessionId: string, text: string): Promise<void> {
    await window.api.post(`/api/v1/rnx/sessions/${sessionId}/input`, {
        text,
        newline: true,
    });
}
