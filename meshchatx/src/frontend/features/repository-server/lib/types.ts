// SPDX-License-Identifier: 0BSD

export interface RepositoryServerHttpInfo {
    running?: boolean;
    host?: string;
    port?: number;
    url?: string;
    last_host?: string;
    last_port?: number;
}

export interface RepositoryServerStatus {
    http?: RepositoryServerHttpInfo;
    last_refresh_failed?: Record<string, string>;
}

export interface RepositoryEntry {
    name: string;
    source: string;
    bytes: number;
}

export interface HttpBodyPayload {
    host?: string;
    port?: number;
}

export interface BuildHttpBodyResult {
    error?: string;
    body?: HttpBodyPayload;
}

export interface HttpActionResponse {
    ok?: boolean;
    error?: string;
    message?: string;
}
