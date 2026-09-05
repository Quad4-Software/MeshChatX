// SPDX-License-Identifier: 0BSD

import type {
    RnshConnectForm,
    RnshConnectPayload,
    RnshListenForm,
    RnshListenPayload,
    RnshSession,
} from "./types.js";

/**
 * Build connect session payload from form values
 */
export function buildRnshConnectPayload(form: RnshConnectForm): RnshConnectPayload {
    return {
        name: form.name.trim() || undefined,
        mode: "connect",
        destination: form.destination.trim(),
        remote_command: form.command.trim() || undefined,
        config_path: form.config_path.trim() || undefined,
        mirror: !!form.mirror,
        no_id: !!form.no_id,
        autostart: true,
    };
}

/**
 * Build listen session payload from form values
 */
export function buildRnshListenPayload(form: RnshListenForm): RnshListenPayload {
    return {
        name: form.name.trim() || undefined,
        mode: "listen",
        allowed_hashes: form.allowed_hashes_text
            .split("\n")
            .map((value) => value.trim())
            .filter((value) => value.length > 0),
        default_command: form.command.trim() || undefined,
        config_path: form.config_path.trim() || undefined,
        no_auth: !!form.no_auth,
        autostart: true,
    };
}

/**
 * Fetch all RNSH sessions
 */
export async function fetchRnshSessions(): Promise<RnshSession[]> {
    const response = await window.api.get("/api/v1/rnsh/sessions");
    const data = response.data as { sessions?: RnshSession[] } | undefined;
    return Array.isArray(data?.sessions) ? data.sessions : [];
}

/**
 * Create a new RNSH session
 */
export async function createRnshSession(
    payload: RnshConnectPayload | RnshListenPayload
): Promise<RnshSession | null> {
    const response = await window.api.post("/api/v1/rnsh/sessions", payload);
    const data = response.data as { session?: RnshSession } | undefined;
    return data?.session || null;
}

/**
 * Start an RNSH session
 */
export async function startRnshSession(sessionId: string): Promise<void> {
    await window.api.post(`/api/v1/rnsh/sessions/${sessionId}/start`, {});
}

/**
 * Stop an RNSH session
 */
export async function stopRnshSession(sessionId: string): Promise<void> {
    await window.api.post(`/api/v1/rnsh/sessions/${sessionId}/stop`, {});
}

/**
 * Remove an RNSH session
 */
export async function removeRnshSession(sessionId: string): Promise<void> {
    await window.api.delete(`/api/v1/rnsh/sessions/${sessionId}`);
}

/**
 * Clear terminal output for an RNSH session
 */
export async function clearRnshSessionOutput(sessionId: string): Promise<RnshSession | null> {
    const response = await window.api.post(`/api/v1/rnsh/sessions/${sessionId}/clear`, {});
    const data = response.data as { session?: RnshSession } | undefined;
    return data?.session || null;
}

/**
 * Send interactive text input to an RNSH session
 */
export async function sendRnshSessionInput(sessionId: string, text: string): Promise<void> {
    await window.api.post(`/api/v1/rnsh/sessions/${sessionId}/input`, {
        text,
        newline: true,
    });
}
