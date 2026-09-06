// SPDX-License-Identifier: 0BSD

import WebSocketConnection from "../../../js/WebSocketConnection.js";

export function isFailedPageContent(content: string | null | undefined): boolean {
    if (!content || typeof content !== "string") {
        return false;
    }
    const lower = content.toLowerCase();
    return (
        lower.includes("failed to load page") ||
        lower.includes("failed loading page") ||
        lower.includes("page load timed out") ||
        lower.includes("page load failed") ||
        lower.includes("nomadnet.failed_to_load_page")
    );
}

export function isCancelledPageContent(content: string | null | undefined): boolean {
    if (!content || typeof content !== "string") {
        return false;
    }
    return (
        content === "nomadnet.page_download_cancelled" ||
        content === "nomadnet.crash_tab_render_cancelled" ||
        content.includes("page_download_cancelled") ||
        content.includes("crash_tab_render_cancelled")
    );
}

export function formatBytes(bytes: number | null | undefined): string {
    if (bytes == null || isNaN(bytes) || bytes < 0) {
        return "0 B";
    }
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatBytesPerSecond(bytesPerSec: number | null | undefined): string {
    if (bytesPerSec == null || isNaN(bytesPerSec) || bytesPerSec < 0) {
        return "0 B/s";
    }
    return `${formatBytes(bytesPerSec)}/s`;
}

export function formatDuration(ms: number | null | undefined): string {
    if (ms == null || isNaN(ms) || ms < 0) {
        return "0s";
    }
    if (ms < 1000) {
        return `${ms}ms`;
    }
    return `${(ms / 1000).toFixed(1)}s`;
}

export interface PageDownloadOptions {
    destinationHash: string;
    pagePath: string;
    fieldData?: unknown;
    isPrivate?: boolean;
}

/** Build outbound nomadnet.page.download payload (backend expects page_path). */
export function createPageDownloadPayload(
    optionsOrHash: string | PageDownloadOptions,
    pagePath = "/page/index.mu",
    isPrivate = false,
    _sequence = 1,
    fieldData: unknown = null
) {
    if (typeof optionsOrHash === "string") {
        return {
            type: "nomadnet.page.download",
            nomadnet_page_download: {
                destination_hash: optionsOrHash,
                page_path: pagePath,
                field_data: fieldData,
                private: Boolean(isPrivate),
            },
        };
    }
    return {
        type: "nomadnet.page.download",
        nomadnet_page_download: {
            destination_hash: optionsOrHash.destinationHash,
            page_path: optionsOrHash.pagePath,
            field_data: optionsOrHash.fieldData ?? fieldData,
            private: Boolean(optionsOrHash.isPrivate ?? isPrivate),
        },
    };
}

export function createPageDownloadRequestPayload(
    optionsOrHash: string | PageDownloadOptions,
    pagePath = "/page/index.mu",
    isPrivate = false,
    sequence = 1,
    fieldData: unknown = null
) {
    return createPageDownloadPayload(optionsOrHash, pagePath, isPrivate, sequence, fieldData);
}

export interface FileDownloadOptions {
    destinationHash: string;
    filePath: string;
    isPrivate?: boolean;
    data?: string | null;
}

export function createFileDownloadPayload(
    optionsOrHash: string | FileDownloadOptions,
    filePath = "",
    isPrivate = false,
    _identifyOnConnect = false,
    data: string | null = null
) {
    if (typeof optionsOrHash === "string") {
        const payload: Record<string, unknown> = {
            destination_hash: optionsOrHash,
            file_path: filePath,
            private: Boolean(isPrivate),
        };
        if (data) {
            payload.data = data;
        }
        return {
            type: "nomadnet.file.download",
            nomadnet_file_download: payload,
        };
    }
    const payload: Record<string, unknown> = {
        destination_hash: optionsOrHash.destinationHash,
        file_path: optionsOrHash.filePath,
        private: Boolean(optionsOrHash.isPrivate),
    };
    if (optionsOrHash.data) {
        payload.data = optionsOrHash.data;
    }
    return {
        type: "nomadnet.file.download",
        nomadnet_file_download: payload,
    };
}

export function createFileDownloadRequestPayload(
    optionsOrHash: string | FileDownloadOptions,
    filePath = "",
    isPrivate = false,
    identifyOnConnect = false,
    data: string | null = null
) {
    return createFileDownloadPayload(optionsOrHash, filePath, isPrivate, identifyOnConnect, data);
}

export function createCancelDownloadPayload(downloadId: string | number | null | undefined) {
    return {
        type: "nomadnet.download.cancel",
        download_id: downloadId,
    };
}

export function createArchivesGetPayload(destinationHash: string, pagePath: string) {
    return {
        type: "nomadnet.page.archives.get",
        destination_hash: destinationHash,
        page_path: pagePath,
    };
}

export function createArchiveLoadPayload(archiveId: string | number, downloadId: number) {
    return {
        type: "nomadnet.page.archive.load",
        archive_id: archiveId,
        download_id: downloadId,
    };
}

export function createArchiveAddPayload(destinationHash: string, pagePath: string, content: string) {
    return {
        type: "nomadnet.page.archive.add",
        destination_hash: destinationHash,
        page_path: pagePath,
        content,
    };
}

/** Send a Nomad WS payload as a JSON string (raw WebSocket requires a string). */
export function sendNomadWs(payload: Record<string, unknown>): boolean {
    try {
        return Boolean(WebSocketConnection.send(JSON.stringify(payload)));
    } catch {
        return false;
    }
}

export type NomadChunkBuffers = Record<string | number, { chunks: Uint8Array[] }>;

export function decodeBase64ToBytes(base64: string | null | undefined): Uint8Array {
    const binary = atob(base64 || "");
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

export function bytesToBase64(bytes: Uint8Array): string {
    let binary = "";
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

export function appendDownloadChunk(
    chunkBuffers: NomadChunkBuffers,
    downloadId: string | number | null | undefined,
    chunkPayload: { chunk_b64?: string | null } | null | undefined
): void {
    if (downloadId == null) {
        return;
    }
    const entry = chunkBuffers[downloadId] || { chunks: [] };
    entry.chunks.push(decodeBase64ToBytes(chunkPayload?.chunk_b64));
    chunkBuffers[downloadId] = entry;
}

export function consumeDownloadChunkBytes(
    chunkBuffers: NomadChunkBuffers,
    downloadId: string | number | null | undefined
): Uint8Array {
    if (downloadId == null) {
        return new Uint8Array(0);
    }
    const entry = chunkBuffers[downloadId];
    delete chunkBuffers[downloadId];
    const chunks = entry?.chunks || [];
    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const merged = new Uint8Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
        merged.set(chunk, offset);
        offset += chunk.length;
    }
    return merged;
}

export function consumeDownloadChunksAsText(
    chunkBuffers: NomadChunkBuffers,
    downloadId: string | number | null | undefined
): string {
    return new TextDecoder("utf-8").decode(consumeDownloadChunkBytes(chunkBuffers, downloadId));
}

export function consumeDownloadChunksAsBase64(
    chunkBuffers: NomadChunkBuffers,
    downloadId: string | number | null | undefined
): string {
    return bytesToBase64(consumeDownloadChunkBytes(chunkBuffers, downloadId));
}

export function discardDownloadChunks(
    chunkBuffers: NomadChunkBuffers,
    downloadId: string | number | null | undefined | unknown
): void {
    if (downloadId == null || (typeof downloadId !== "string" && typeof downloadId !== "number")) {
        return;
    }
    delete chunkBuffers[downloadId];
}

export function relativePagePathFromCombined(nodePagePath: string | null | undefined): string {
    if (!nodePagePath) {
        return "";
    }
    if (nodePagePath.includes(":")) {
        return nodePagePath.split(":").slice(1).join(":");
    }
    return nodePagePath;
}
