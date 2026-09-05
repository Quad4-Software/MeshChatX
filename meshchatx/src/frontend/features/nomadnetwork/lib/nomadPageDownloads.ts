// SPDX-License-Identifier: 0BSD

export function isFailedPageContent(content: string | null | undefined): boolean {
    if (!content || typeof content !== "string") {
        return false;
    }
    const lower = content.toLowerCase();
    return (
        lower.includes("failed to load page") ||
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
    sequence?: number;
    isPrivate?: boolean;
    identifyOnConnect?: boolean;
}

export function createPageDownloadPayload(
    optionsOrHash: string | PageDownloadOptions,
    pagePath = "/page/index.mu",
    isPrivate = false,
    sequence = 1,
    identifyOnConnect = false
) {
    if (typeof optionsOrHash === "string") {
        return {
            type: "nomadnet.page.download",
            nomadnet_page_download: {
                destination_hash: optionsOrHash,
                path: pagePath,
                sequence: sequence ?? 1,
                private: Boolean(isPrivate),
                identify: Boolean(identifyOnConnect),
            },
        };
    }
    return {
        type: "nomadnet.page.download",
        nomadnet_page_download: {
            destination_hash: optionsOrHash.destinationHash,
            path: optionsOrHash.pagePath,
            sequence: optionsOrHash.sequence ?? 1,
            private: Boolean(optionsOrHash.isPrivate),
            identify: Boolean(optionsOrHash.identifyOnConnect),
        },
    };
}

export function createPageDownloadRequestPayload(
    optionsOrHash: string | PageDownloadOptions,
    pagePath = "/page/index.mu",
    isPrivate = false,
    sequence = 1,
    identifyOnConnect = false
) {
    const payload = createPageDownloadPayload(optionsOrHash, pagePath, isPrivate, sequence, identifyOnConnect);
    const destHash = typeof optionsOrHash === "string" ? optionsOrHash : optionsOrHash.destinationHash;
    const pPath = typeof optionsOrHash === "string" ? pagePath : optionsOrHash.pagePath;
    const seq = typeof optionsOrHash === "string" ? (sequence ?? 1) : (optionsOrHash.sequence ?? 1);
    return {
        ...payload,
        request_id: `${destHash}:${pPath}:${seq}`,
    };
}

export interface FileDownloadOptions {
    destinationHash: string;
    filePath: string;
    isPrivate?: boolean;
    identifyOnConnect?: boolean;
    data?: string | null;
}

export function createFileDownloadPayload(
    optionsOrHash: string | FileDownloadOptions,
    filePath = "",
    isPrivate = false,
    identifyOnConnect = false,
    data: string | null = null
) {
    if (typeof optionsOrHash === "string") {
        const payload: Record<string, unknown> = {
            destination_hash: optionsOrHash,
            path: filePath,
            private: Boolean(isPrivate),
            identify: Boolean(identifyOnConnect),
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
        path: optionsOrHash.filePath,
        private: Boolean(optionsOrHash.isPrivate),
        identify: Boolean(optionsOrHash.identifyOnConnect),
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

export function createCancelDownloadPayload(
    optionsOrId?:
        | string
        | {
              downloadId?: string | null;
              destinationHash?: string | null;
          }
        | null
) {
    if (typeof optionsOrId === "string") {
        return {
            type: "nomadnet.download.cancel",
            nomadnet_download_cancel: {
                download_id: optionsOrId,
                destination_hash: undefined,
            },
        };
    }
    return {
        type: "nomadnet.download.cancel",
        nomadnet_download_cancel: {
            download_id: optionsOrId?.downloadId || undefined,
            destination_hash: optionsOrId?.destinationHash || undefined,
        },
    };
}
