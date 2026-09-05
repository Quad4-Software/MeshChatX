// SPDX-License-Identifier: 0BSD

import { renderTerminalOutput } from "../../../js/terminalRender.js";
import { MAX_OUTPUT_BUFFER_LENGTH } from "./constants.js";
import type { RemoteShellSession } from "./types.js";

/**
 * Ingest full or partial session output payload safely into outputs map
 */
export function ingestSessionOutput(
    session: RemoteShellSession | null | undefined,
    outputsBySession: Record<string, string>
): void {
    if (!session || !session.id) {
        return;
    }
    const existing = outputsBySession[session.id] || "";
    const chunks = Array.isArray(session.output_chunks) ? session.output_chunks : [];
    const fromChunks = chunks.length > 0 ? chunks.map((chunk) => chunk.text || "").join("") : "";
    const fromText = typeof session.output_text === "string" ? session.output_text : "";
    const incoming = fromText.length >= fromChunks.length ? fromText : fromChunks;

    if (!incoming) {
        if (!Object.prototype.hasOwnProperty.call(outputsBySession, session.id)) {
            outputsBySession[session.id] = "";
        }
        return;
    }

    if (existing.length > incoming.length) {
        if (
            existing.endsWith(incoming) ||
            (fromChunks && existing.endsWith(fromChunks)) ||
            (fromChunks && existing.includes(fromChunks))
        ) {
            return;
        }
    }
    outputsBySession[session.id] = incoming;
}

/**
 * Append incoming stream text to a session buffer with boundary clamping
 */
export function appendSessionOutput(
    sessionId: string | undefined,
    text: string | undefined,
    outputsBySession: Record<string, string>
): void {
    if (!sessionId || typeof text !== "string" || text.length === 0) {
        return;
    }
    const existing = outputsBySession[sessionId] || "";
    const merged = existing + text;
    outputsBySession[sessionId] =
        merged.length > MAX_OUTPUT_BUFFER_LENGTH ? merged.slice(-MAX_OUTPUT_BUFFER_LENGTH) : merged;
}

/**
 * Format raw output text for terminal presentation
 */
export function formatTerminalOutput(
    selectedSessionId: string | null,
    outputRaw: string | undefined,
    selectPrompt: string,
    emptyPrompt: string
): string {
    if (!selectedSessionId) {
        return selectPrompt;
    }
    if (typeof outputRaw === "string" && outputRaw.length > 0) {
        return renderTerminalOutput(outputRaw);
    }
    return emptyPrompt;
}

/**
 * Resolve session status badge color classes
 */
export function getSessionStatusClass(session: RemoteShellSession | null | undefined): string {
    if (!session) return "text-gray-500";
    if (session.status === "running") return "text-emerald-600 dark:text-emerald-400";
    if (session.status === "failed") return "text-red-600 dark:text-red-400";
    return "text-sem-fg-muted";
}

/**
 * Resolve session display subtitle
 */
export function getSessionSubtitle(session: RemoteShellSession | null | undefined, listenModeLabel: string): string {
    if (!session) return "-";
    if (session.mode === "listen") {
        return session.listen_address || listenModeLabel;
    }
    return session.destination || "-";
}
