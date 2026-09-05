// SPDX-License-Identifier: 0BSD

import { reactive } from "vue";

export type FatalErrorKind = "frontend" | "backend";

export type FatalErrorRecord = {
    kind: FatalErrorKind;
    title: string;
    message: string;
    details?: string;
    stack?: string;
    context?: string;
    timestamp: number;
};

type FatalErrorState = {
    active: FatalErrorRecord | null;
    bootFailure: FatalErrorRecord | null;
};

const fatalErrorState = reactive<FatalErrorState>({
    active: null,
    bootFailure: null,
});

export function buildFatalErrorRecord(
    payload: Partial<FatalErrorRecord> & { kind: FatalErrorKind; message: string }
): FatalErrorRecord {
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

export function reportFatalError(payload: Partial<FatalErrorRecord> & { kind: FatalErrorKind; message: string }): void {
    fatalErrorState.active = buildFatalErrorRecord(payload);
    void recordFatalErrorLocally(fatalErrorState.active);
}

export async function recordFatalErrorLocally(
    record: FatalErrorRecord | null | undefined
): Promise<Record<string, unknown> | null> {
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

export function reportBootFailure(
    payload: Partial<FatalErrorRecord> & { kind: FatalErrorKind; message: string }
): FatalErrorRecord {
    const record = buildFatalErrorRecord(payload);
    fatalErrorState.bootFailure = record;
    fatalErrorState.active = record;
    return record;
}

export function clearFatalError(): void {
    fatalErrorState.active = null;
}

export function formatFatalErrorReport(record: FatalErrorRecord | null | undefined): string {
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
