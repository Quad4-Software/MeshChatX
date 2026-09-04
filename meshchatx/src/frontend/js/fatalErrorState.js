// SPDX-License-Identifier: 0BSD

import { reactive } from "vue";

/** @typedef {"frontend" | "backend"} FatalErrorKind */

/**
 * @typedef {object} FatalErrorRecord
 * @property {FatalErrorKind} kind
 * @property {string} title
 * @property {string} message
 * @property {string} [details]
 * @property {string} [stack]
 * @property {string} [context]
 * @property {number} timestamp
 */

const fatalErrorState = reactive({
    active: null,
    bootFailure: null,
});

/**
 * @param {Partial<FatalErrorRecord> & { kind: FatalErrorKind, message: string }} payload
 * @returns {FatalErrorRecord}
 */
export function buildFatalErrorRecord(payload) {
    const message = String(payload.message || "Unknown error");
    return {
        kind: payload.kind,
        title: payload.title || "",
        message,
        details: payload.details ? String(payload.details) : "",
        stack: payload.stack ? String(payload.stack) : "",
        context: payload.context ? String(payload.context) : "",
        timestamp: payload.timestamp || Date.now(),
    };
}

/**
 * @param {Partial<FatalErrorRecord> & { kind: FatalErrorKind, message: string }} payload
 */
export function reportFatalError(payload) {
    fatalErrorState.active = buildFatalErrorRecord(payload);
    void recordFatalErrorLocally(fatalErrorState.active);
}

/**
 * @param {FatalErrorRecord | null | undefined} record
 */
export async function recordFatalErrorLocally(record) {
    if (!record || typeof window === "undefined" || !window.api?.post) {
        return null;
    }
    try {
        const response = await window.api.post("/api/v1/bug-reports/local", {
            title: record.title || record.message,
            description: record.details || record.context || "",
            exception: {
                type: record.kind === "backend" ? "BackendError" : "FrontendError",
                value: record.message,
                stack: record.stack || "",
            },
            source: record.kind === "backend" ? "backend" : "frontend",
            kind: "exception",
            meta: {
                context: record.context || "",
            },
            force: true,
        });
        return response?.data || null;
    } catch {
        return null;
    }
}

/**
 * @param {Partial<FatalErrorRecord> & { kind: FatalErrorKind, message: string }} payload
 */
export function reportBootFailure(payload) {
    const record = buildFatalErrorRecord(payload);
    fatalErrorState.bootFailure = record;
    fatalErrorState.active = record;
    return record;
}

export function clearFatalError() {
    fatalErrorState.active = null;
}

/**
 * @param {FatalErrorRecord | null | undefined} record
 * @returns {string}
 */
export function formatFatalErrorReport(record) {
    if (!record) {
        return "";
    }
    const lines = [
        "MeshChatX error report",
        `Kind: ${record.kind}`,
        `Time: ${new Date(record.timestamp).toISOString()}`,
    ];
    if (record.title) {
        lines.push(`Title: ${record.title}`);
    }
    lines.push(`Message: ${record.message}`);
    if (record.context) {
        lines.push(`Context: ${record.context}`);
    }
    if (record.details) {
        lines.push("", "Details:", record.details);
    }
    if (record.stack) {
        lines.push("", "Stack:", record.stack);
    }
    if (typeof navigator !== "undefined" && navigator.userAgent) {
        lines.push("", `User agent: ${navigator.userAgent}`);
    }
    if (typeof window !== "undefined" && window.location?.href) {
        lines.push(`Location: ${window.location.href}`);
    }
    return lines.join("\n");
}

export default fatalErrorState;
