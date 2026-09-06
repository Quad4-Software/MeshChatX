// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import DownloadUtils from "../../../js/DownloadUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import { DEFAULT_PAGE_PATH } from "./constants.js";
import { requestPageArchives } from "./nomadPageArchives.js";
import {
    appendDownloadChunk,
    consumeDownloadChunksAsBase64,
    consumeDownloadChunksAsText,
    discardDownloadChunks,
    sendNomadWs,
    createCancelDownloadPayload,
    type NomadChunkBuffers,
} from "./nomadPageDownloads.js";
import type { NomadNode, NomadPageArchive } from "./types.js";

export type NomadPageDownloadSnapshot = {
    active: boolean;
    isPrivate: boolean;
    currentPageDownloadId: number | string | null;
    pendingPageCancelWithoutId: boolean;
    currentFileDownloadId: number | string | null;
    nodeFilePath: string | null;
    selectedNode: NomadNode | null;
    relativePagePath: string;
    nodePagePath: string | null;
    nodePageCache: Record<string, string>;
    nomadPageDownloadChunkBuffers: NomadChunkBuffers;
    nomadFileDownloadChunkBuffers: NomadChunkBuffers;
};

export type NomadPageDownloadPatch = Partial<{
    currentPageDownloadId: number | string | null;
    pendingPageCancelWithoutId: boolean;
    currentFileDownloadId: number | string | null;
    downloadTotalBytes: number;
    downloadBytesReceived: number;
    nodePagePath: string | null;
    nodePagePathUrlInput: string;
    isShowingArchivedVersion: boolean;
    archivedAt: string | null;
    nodePageContent: string | null;
    isLoadingNodePage: boolean;
    nodePageCache: Record<string, string>;
    isDownloadingNodeFile: boolean;
    nodeFilePath: string | null;
    nodeFileProgress: number;
    nodeFileDownloadSpeed: number | null;
    pageRenderAborted: boolean;
    pageArchives: NomadPageArchive[];
}>;

export type NomadPageDownloadAccess = {
    get: () => NomadPageDownloadSnapshot;
    apply: (patch: NomadPageDownloadPatch) => void;
    clearPageLoadTimeout: () => void;
    ontabtitlechange?: (title: string) => void;
};

function ownsPageDownload(
    s: NomadPageDownloadSnapshot,
    body: Record<string, unknown> | null | undefined,
    downloadId: number | string | null | undefined
): boolean {
    if (!body || typeof body !== "object") return false;
    if (s.currentPageDownloadId != null && downloadId != null && s.currentPageDownloadId === downloadId) {
        return true;
    }
    const dest = String(body.destination_hash || "");
    const path = String(body.page_path || "");
    if (!s.selectedNode?.destination_hash || !dest) return false;
    if (dest !== s.selectedNode.destination_hash) return false;
    if (!path) return true;
    return path === s.relativePagePath || path === s.nodePagePath;
}

export function onNomadPageDownloadEvent(access: NomadPageDownloadAccess, json: Record<string, unknown>): void {
    const s = access.get();
    if (!s.active && s.currentPageDownloadId == null) return;
    let body = (json.nomadnet_page_download || null) as Record<string, unknown> | null;
    const downloadId = json.download_id as number | string | undefined;
    if (!body || !ownsPageDownload(s, body, downloadId)) return;

    if (body.status === "started") {
        if (s.pendingPageCancelWithoutId) {
            access.apply({ pendingPageCancelWithoutId: false });
            sendNomadWs(createCancelDownloadPayload(downloadId));
            return;
        }
        access.apply({ currentPageDownloadId: downloadId ?? null });
        return;
    }

    if (body.status === "chunk") {
        appendDownloadChunk(s.nomadPageDownloadChunkBuffers, downloadId, body);
        const total = Number(body.total || 0);
        const offset = Number(body.offset || 0);
        if (total > 0) {
            access.apply({
                downloadTotalBytes: total,
                downloadBytesReceived: Math.min(total, offset),
            });
        }
        return;
    }

    if (body.status === "phase") {
        if (s.currentPageDownloadId !== downloadId) return;
        return;
    }

    if (body.status === "progress") {
        if (s.currentPageDownloadId != null && s.currentPageDownloadId !== downloadId) return;
        const progress = Number(body.progress || 0);
        const patch: NomadPageDownloadPatch = { downloadBytesReceived: progress };
        if (progress > 0 && progress <= 1) {
            patch.downloadTotalBytes = 1;
        }
        access.apply(patch);
        return;
    }

    if (body.status === "success" && body.chunked) {
        body = {
            ...body,
            page_content: consumeDownloadChunksAsText(s.nomadPageDownloadChunkBuffers, downloadId),
        };
    } else if (downloadId != null) {
        discardDownloadChunks(s.nomadPageDownloadChunkBuffers, downloadId);
    }

    if (body.status === "success" && body.is_archived_version) {
        access.clearPageLoadTimeout();
        const dest = String(body.destination_hash || s.selectedNode?.destination_hash || "");
        const path = String(body.page_path || s.relativePagePath || DEFAULT_PAGE_PATH);
        const combined = `${dest}:${path}`;
        access.apply({
            nodePagePath: combined,
            nodePagePathUrlInput: combined,
            isShowingArchivedVersion: true,
            archivedAt: body.archived_at != null ? String(body.archived_at) : null,
            nodePageContent: typeof body.page_content === "string" ? body.page_content : "",
            isLoadingNodePage: false,
            currentPageDownloadId: null,
        });
        if (!s.isPrivate && dest) {
            requestPageArchives(dest, path);
        }
        return;
    }

    if (body.status === "success") {
        access.clearPageLoadTimeout();
        const content = typeof body.page_content === "string" ? body.page_content : "";
        const patch: NomadPageDownloadPatch = {
            isLoadingNodePage: false,
            nodePageContent: content,
            isShowingArchivedVersion: false,
            archivedAt: null,
            currentPageDownloadId: null,
        };
        if (!s.isPrivate && s.selectedNode?.destination_hash && s.relativePagePath && content != null) {
            patch.nodePageCache = {
                ...s.nodePageCache,
                [`${s.selectedNode.destination_hash}:${s.relativePagePath}`]: content,
            };
        }
        access.apply(patch);
        access.ontabtitlechange?.(s.selectedNode?.custom_display_name || s.selectedNode?.display_name || "Nomad");
        if (!s.isPrivate && s.selectedNode?.destination_hash && s.relativePagePath) {
            requestPageArchives(s.selectedNode.destination_hash, s.relativePagePath);
        }
        return;
    }

    if (body.status === "failure") {
        access.clearPageLoadTimeout();
        const reason = String(body.failure_reason || t("nomadnet.failed_to_load_page"));
        access.apply({
            isLoadingNodePage: false,
            currentPageDownloadId: null,
            nodePageContent: `Failed loading page: ${reason}`,
        });
        ToastUtils.error(t("nomadnet.failed_to_load_page"));
    }
}

export function onNomadFileDownloadEvent(access: NomadPageDownloadAccess, json: Record<string, unknown>): void {
    const s = access.get();
    let body = (json.nomadnet_file_download || null) as Record<string, unknown> | null;
    const downloadId = json.download_id as number | string | undefined;
    if (!body) return;

    if (body.status === "started") {
        access.apply({
            currentFileDownloadId: downloadId ?? null,
            isDownloadingNodeFile: true,
            nodeFilePath: String(body.file_path || ""),
        });
        return;
    }
    if (s.currentFileDownloadId != null && downloadId != null && s.currentFileDownloadId !== downloadId) {
        return;
    }
    if (body.status === "chunk") {
        appendDownloadChunk(s.nomadFileDownloadChunkBuffers, downloadId, body);
        const total = Number(body.total || 0);
        const offset = Number(body.offset || 0);
        const patch: NomadPageDownloadPatch = {
            isDownloadingNodeFile: true,
            nodeFilePath: String(body.file_path || s.nodeFilePath || ""),
        };
        if (total > 0) {
            patch.nodeFileProgress = Math.round((Math.min(total, offset) / total) * 100);
        }
        access.apply(patch);
        return;
    }
    if (body.status === "progress") {
        access.apply({
            isDownloadingNodeFile: true,
            nodeFileProgress: Number(body.progress || 0),
            nodeFilePath: String(body.file_path || s.nodeFilePath || ""),
        });
        return;
    }
    if (body.status === "success") {
        let fileBytesBase64 = typeof body.file_bytes === "string" ? body.file_bytes : "";
        if (body.chunked) {
            fileBytesBase64 = consumeDownloadChunksAsBase64(s.nomadFileDownloadChunkBuffers, downloadId);
        } else if (downloadId != null) {
            discardDownloadChunks(s.nomadFileDownloadChunkBuffers, downloadId);
        }
        access.apply({
            isDownloadingNodeFile: false,
            currentFileDownloadId: null,
        });
        const fileName = String(body.file_name || body.file_path || "download");
        if (fileBytesBase64) {
            try {
                DownloadUtils.downloadFromBase64(fileName, fileBytesBase64);
                ToastUtils.success(t("nomadnet.file_download_complete"));
            } catch (e) {
                console.error("nomad file download save failed", e);
                ToastUtils.error(t("nomadnet.download_page_failed"));
            }
        } else {
            DialogUtils.alert(t("nomadnet.file_download_complete"));
        }
        return;
    }
    if (body.status === "failure") {
        if (downloadId != null) {
            discardDownloadChunks(s.nomadFileDownloadChunkBuffers, downloadId);
        }
        access.apply({
            isDownloadingNodeFile: false,
            currentFileDownloadId: null,
        });
        ToastUtils.error(String(body.failure_reason || t("nomadnet.download_page_failed")));
    }
}

export function onNomadDownloadCancelledEvent(access: NomadPageDownloadAccess, json: Record<string, unknown>): void {
    const s = access.get();
    const downloadId = json.download_id;
    if (s.currentPageDownloadId != null && s.currentPageDownloadId === downloadId) {
        access.clearPageLoadTimeout();
        discardDownloadChunks(s.nomadPageDownloadChunkBuffers, downloadId);
        access.apply({
            currentPageDownloadId: null,
            pendingPageCancelWithoutId: false,
            isLoadingNodePage: false,
            pageRenderAborted: true,
            nodePageContent: "nomadnet.page_download_cancelled",
        });
    }
    if (s.currentFileDownloadId != null && s.currentFileDownloadId === downloadId) {
        discardDownloadChunks(s.nomadFileDownloadChunkBuffers, downloadId);
        access.apply({
            currentFileDownloadId: null,
            isDownloadingNodeFile: false,
            nodeFileDownloadSpeed: null,
        });
    }
}

export function onNomadPageArchivesEvent(access: NomadPageDownloadAccess, json: Record<string, unknown>): void {
    const s = access.get();
    if (s.isPrivate) return;
    const dest = String(json.destination_hash || "");
    const path = String(json.page_path || "");
    if (!s.selectedNode?.destination_hash || dest !== s.selectedNode.destination_hash) return;
    if (path && path !== s.relativePagePath && path !== s.nodePagePath) return;
    access.apply({
        pageArchives: Array.isArray(json.archives) ? (json.archives as NomadPageArchive[]) : [],
    });
}

export function onNomadPageArchiveAddedEvent(access: NomadPageDownloadAccess, json: Record<string, unknown>): void {
    const s = access.get();
    if (s.isPrivate) return;
    const dest = String(json.destination_hash || "");
    const path = String(json.page_path || "");
    if (!s.selectedNode?.destination_hash || dest !== s.selectedNode.destination_hash) return;
    if (path && path !== s.relativePagePath && path !== s.nodePagePath) return;
    ToastUtils.success(t("nomadnet.page_archived_successfully"));
    requestPageArchives(dest, s.relativePagePath || path);
}
