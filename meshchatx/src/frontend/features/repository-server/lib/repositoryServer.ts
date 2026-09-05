// SPDX-License-Identifier: 0BSD

import LinkUtils from "../../../js/LinkUtils.js";
import { t } from "../../../js/i18n.js";
import {
    API_REPOSITORY_SERVER_HTTP_RESTART,
    API_REPOSITORY_SERVER_HTTP_START,
    API_REPOSITORY_SERVER_HTTP_STOP,
    API_REPOSITORY_SERVER_LIST,
    API_REPOSITORY_SERVER_STATUS,
    API_REPOSITORY_SERVER_UPLOAD,
    DEFAULT_HTTP_HOST,
    DEFAULT_HTTP_PORT,
} from "./constants.js";
import type {
    BuildHttpBodyResult,
    HttpActionResponse,
    HttpBodyPayload,
    RepositoryEntry,
    RepositoryServerStatus,
} from "./types.js";

/**
 * Format bytes into human readable binary unit strings
 */
export function formatBytes(n: number): string {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Validate and format the browser repo URL with host replacement and allowlist check
 */
export function computeBrowserRepoUrl(raw?: string | null): string | null {
    if (!raw) {
        return null;
    }
    let candidate = String(raw).trim();
    try {
        const parsed = new URL(candidate);
        if (parsed.hostname === "0.0.0.0" && typeof window !== "undefined" && window.location?.hostname) {
            parsed.hostname = window.location.hostname;
        }
        candidate = parsed.toString();
    } catch {
        // Fall through to http allowlist check below
    }
    return LinkUtils.httpUrlHrefOrNull(candidate);
}

/**
 * Synchronize HTTP form fields host and port from server status
 */
export function syncHttpFormFromStatus(
    status?: RepositoryServerStatus | null,
    currentHost = DEFAULT_HTTP_HOST,
    currentPort = DEFAULT_HTTP_PORT
): { host: string; port: string } {
    const h = status?.http;
    if (!h) {
        return { host: currentHost, port: currentPort };
    }
    let host = currentHost;
    let port = currentPort;
    if (h.running) {
        if (h.host) {
            host = h.host;
        }
        if (h.port != null) {
            port = String(h.port);
        }
    } else if (h.last_host) {
        host = h.last_host;
        port = h.last_port != null ? String(h.last_port) : DEFAULT_HTTP_PORT;
    }
    return { host, port };
}

/**
 * Build HTTP start/restart payload from user inputs
 */
export function buildHttpBody(host: string, port: string): BuildHttpBodyResult {
    const body: HttpBodyPayload = {};
    const hostTrimmed = (host || "").trim();
    if (hostTrimmed) {
        body.host = hostTrimmed;
    }
    const portRaw = (port || "").trim();
    if (portRaw !== "") {
        const p = parseInt(portRaw, 10);
        if (!Number.isFinite(p)) {
            return { error: "invalid_port" };
        }
        body.port = p;
    }
    return { body };
}

/**
 * Resolve localized error message for HTTP server operations
 */
export function resolveHttpErrorMessage(errKey?: string, detail?: string): string {
    const map: Record<string, string> = {
        invalid_host: t("tools.repository_server.http_err_invalid_host"),
        invalid_port: t("tools.repository_server.http_err_invalid_port"),
        already_running: t("tools.repository_server.http_err_already_running"),
        bind_failed: t("tools.repository_server.http_err_bind_failed"),
    };
    let msg = (errKey ? map[errKey] : undefined) || t("tools.repository_server.http_err_generic");
    if (errKey === "bind_failed" && detail) {
        msg = `${msg}: ${detail}`;
    } else if (errKey && !map[errKey] && detail) {
        msg = `${msg}: ${detail}`;
    }
    return msg;
}

/**
 * Fetch repository server status
 */
export async function fetchRepositoryStatus(): Promise<RepositoryServerStatus> {
    const res = await window.api.get(API_REPOSITORY_SERVER_STATUS);
    return (res.data || {}) as RepositoryServerStatus;
}

/**
 * Fetch repository server entries list
 */
export async function fetchRepositoryList(): Promise<RepositoryEntry[]> {
    const res = await window.api.get(API_REPOSITORY_SERVER_LIST);
    return Array.isArray(res.data) ? (res.data as RepositoryEntry[]) : [];
}

/**
 * Start repository HTTP server
 */
export async function startHttpServer(payload: HttpBodyPayload): Promise<HttpActionResponse> {
    const res = await window.api.post(API_REPOSITORY_SERVER_HTTP_START, payload);
    return (res.data || {}) as HttpActionResponse;
}

/**
 * Stop repository HTTP server
 */
export async function stopHttpServer(): Promise<HttpActionResponse> {
    const res = await window.api.post(API_REPOSITORY_SERVER_HTTP_STOP);
    return (res.data || {}) as HttpActionResponse;
}

/**
 * Restart repository HTTP server
 */
export async function restartHttpServer(payload: HttpBodyPayload): Promise<HttpActionResponse> {
    const res = await window.api.post(API_REPOSITORY_SERVER_HTTP_RESTART, payload);
    return (res.data || {}) as HttpActionResponse;
}

/**
 * Upload package file to repository server
 */
export async function uploadRepositoryPackage(file: File): Promise<void> {
    const form = new FormData();
    form.append("file", file, file.name);
    await window.api.post(API_REPOSITORY_SERVER_UPLOAD, form);
}

/**
 * Delete uploaded package from repository server
 */
export async function deleteRepositoryUpload(name: string): Promise<void> {
    const enc = encodeURIComponent(name);
    await window.api.delete(`${API_REPOSITORY_SERVER_UPLOAD}/${enc}`);
}
