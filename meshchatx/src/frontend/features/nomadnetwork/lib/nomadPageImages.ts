// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import { DEFAULT_PAGE_PATH } from "./constants.js";
import {
    appendDownloadChunk,
    consumeDownloadChunksAsBase64,
    discardDownloadChunks,
    formatBytes,
    resendInFlightDownloadRequests,
    sendNomadWs,
    type NomadChunkBuffers,
    type NomadInFlightDownloadContext,
} from "./nomadPageDownloads.js";

export type NomadImagePolicy = "never" | "manual" | "auto" | "always";
const NOMAD_IMAGE_POLICIES: readonly NomadImagePolicy[] = ["never", "manual", "auto", "always"];
const NOMAD_IMAGE_CACHE_MAX_ENTRIES = 64;

export interface NomadCrashTabImage {
    url?: string;
    path?: string;
    alt?: string;
    w?: string | null;
    h?: string | null;
    size?: string | null;
    key?: string;
    align?: string;
    profile?: string;
}

export interface NomadImageDownloadContext extends NomadInFlightDownloadContext {
    destinationHash: string;
    filePath: string;
    requestId: string;
}

export function sanitizeNomadImagePolicy(value: unknown): NomadImagePolicy | null {
    const policy = String(value || "")
        .trim()
        .toLowerCase();
    return (NOMAD_IMAGE_POLICIES as readonly string[]).includes(policy) ? (policy as NomadImagePolicy) : null;
}

/** Per-node override wins, then the global config policy, then manual. */
export function resolveNomadImagePolicy(perNode: unknown, globalPolicy: unknown): NomadImagePolicy {
    return sanitizeNomadImagePolicy(perNode) ?? sanitizeNomadImagePolicy(globalPolicy) ?? "manual";
}

function parseNomadImageUrl(raw: string): { destinationHash: string | null; path: string } | null {
    const url = (raw || "").trim();
    if (!url) {
        return null;
    }
    const stripQuery = (path: string) => {
        const q = path.indexOf("?");
        return q >= 0 ? path.substring(0, q) : path;
    };
    if (url.startsWith(":")) {
        const path = url.substring(1) || DEFAULT_PAGE_PATH;
        return { destinationHash: null, path: stripQuery(path) };
    }
    if (url.includes(":")) {
        const idx = url.indexOf(":");
        const hash = url.substring(0, idx);
        if (hash.length === 32) {
            return { destinationHash: hash, path: stripQuery(url.substring(idx + 1)) };
        }
    }
    if (url.startsWith("/page/") || url.startsWith("/file/") || url.startsWith("/media/")) {
        return { destinationHash: null, path: stripQuery(url) };
    }
    if (url.length === 32) {
        return { destinationHash: url, path: DEFAULT_PAGE_PATH };
    }
    return null;
}

/**
 * Resolve a micron image src to a destination hash plus file path.
 * Relative ":/file/img.webp" resolves against the selected node, absolute
 * "<hash>:/file/img.webp" uses the embedded hash. Anything that is not a
 * media/file image path, or that contains traversal or dangerous characters,
 * resolves to empty strings.
 */
export function resolveNomadImageDestination(
    src: string | null | undefined,
    fallbackHash: string | null | undefined
): { destinationHash: string; filePath: string } {
    const reject = { destinationHash: "", filePath: "" };
    const parsed = parseNomadImageUrl(src || "");
    const destinationHash = (parsed?.destinationHash || fallbackHash || "").toLowerCase();
    let filePath = (parsed?.path || "").trim();
    const backtickIndex = filePath.indexOf("`");
    if (backtickIndex >= 0) {
        filePath = filePath.substring(0, backtickIndex);
    }
    if (!/^[a-f0-9]{32}$/.test(destinationHash)) {
        return reject;
    }
    const cleanFilePath = filePath.startsWith("/") ? filePath.slice(1) : filePath;
    if (cleanFilePath.startsWith("media/")) {
        if (!/\.(webp|png|jpe?g|bmp|gif|tiff)$/i.test(cleanFilePath)) {
            return reject;
        }
    } else if (cleanFilePath.startsWith("file/")) {
        if (!/\.webp$/i.test(cleanFilePath)) {
            return reject;
        }
    } else {
        return reject;
    }
    if (
        cleanFilePath.includes("..") ||
        [...cleanFilePath].some((ch) => ch.charCodeAt(0) < 32 || '<>"|?*'.includes(ch))
    ) {
        return reject;
    }
    return { destinationHash, filePath };
}

export function nomadImageCacheKey(destinationHash: string, filePath: string): string {
    return `${destinationHash || ""}:${filePath || ""}`;
}

export function setNomadImageCacheEntry(
    cache: Map<string, { dataUrl: string | null; size: string }>,
    cacheKey: string,
    value: { dataUrl: string | null; size: string },
    isPrivate: boolean
): void {
    if (isPrivate || !cacheKey) {
        return;
    }
    // Simple LRU: evict the oldest entry once the cache is full.
    if (cache.size >= NOMAD_IMAGE_CACHE_MAX_ENTRIES && !cache.has(cacheKey)) {
        const firstKey = cache.keys().next().value;
        if (firstKey !== undefined) {
            cache.delete(firstKey);
        }
    }
    cache.set(cacheKey, value);
}

/** Byte-sniff the real image type from a base64 payload (webp default). */
export function detectNomadImageMimeFromBase64(fileBytes: string | null | undefined): string {
    if (typeof fileBytes !== "string" || fileBytes.length === 0) {
        return "image/webp";
    }
    const needed = 24;
    const chars = Math.ceil((needed / 3) * 4);
    let prefix = fileBytes.slice(0, chars);
    while (prefix.length % 4 !== 0) {
        prefix += "=";
    }
    try {
        const raw = atob(prefix);
        const bytes = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i++) {
            bytes[i] = raw.charCodeAt(i);
        }
        if (bytes.length >= 3 && bytes[0] === 0x47 && bytes[1] === 0x49 && bytes[2] === 0x46) {
            return "image/gif";
        }
        if (bytes.length >= 4 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) {
            return "image/png";
        }
        if (bytes.length >= 2 && bytes[0] === 0xff && bytes[1] === 0xd8) {
            return "image/jpeg";
        }
        if (bytes.length >= 2 && bytes[0] === 0x42 && bytes[1] === 0x4d) {
            return "image/bmp";
        }
        if (
            bytes.length >= 12 &&
            bytes[0] === 0x52 &&
            bytes[1] === 0x49 &&
            bytes[2] === 0x46 &&
            bytes[3] === 0x46 &&
            bytes[8] === 0x57 &&
            bytes[9] === 0x45 &&
            bytes[10] === 0x42 &&
            bytes[11] === 0x50
        ) {
            return "image/webp";
        }
        if (
            bytes.length >= 4 &&
            ((bytes[0] === 0x49 && bytes[1] === 0x49 && bytes[2] === 0x2a && bytes[3] === 0x00) ||
                (bytes[0] === 0x4d && bytes[1] === 0x4d && bytes[2] === 0x00 && bytes[3] === 0x2a))
        ) {
            return "image/tiff";
        }
    } catch {
        return "image/webp";
    }
    return "image/webp";
}

export function getNomadImageDataUrl(fileBytes: string | null | undefined): string | null {
    if (!fileBytes) {
        return null;
    }
    return `data:${detectNomadImageMimeFromBase64(fileBytes)};base64,${fileBytes}`;
}

export function generateNomadImageRequestId(): string {
    return `${Date.now()}-${Math.floor(Math.random() * 1_000_000)}`;
}

/** Outbound file download payload carrying image metadata plus request_id. */
export function createNomadImageDownloadPayload(
    destinationHash: string,
    filePath: string,
    isPrivate: boolean,
    data: Record<string, unknown> | null
): Record<string, unknown> {
    const body: Record<string, unknown> = {
        destination_hash: destinationHash,
        file_path: filePath,
        private: Boolean(isPrivate),
    };
    const payload: Record<string, unknown> = {
        type: "nomadnet.file.download",
        nomadnet_file_download: body,
    };
    if (data != null) {
        body.data = data;
        if (data.request_id) {
            payload.request_id = data.request_id;
        }
    }
    return payload;
}

/** A ws event only owns an image download when ids and target match. */
export function ownsNomadImageDownloadEvent(
    context: NomadImageDownloadContext | null | undefined,
    body: Record<string, unknown> | null | undefined,
    topLevel: Record<string, unknown> | null | undefined
): boolean {
    if (!context || !body) {
        return false;
    }
    const data = (body.data || null) as Record<string, unknown> | null;
    const eventRequestId = body.request_id ?? data?.request_id ?? topLevel?.request_id;
    if (eventRequestId != null && String(eventRequestId) !== String(context.requestId)) {
        return false;
    }
    const eventDownloadId = topLevel?.download_id ?? body.download_id;
    if (
        eventDownloadId != null &&
        context.downloadId != null &&
        Number(eventDownloadId) !== Number(context.downloadId)
    ) {
        return false;
    }
    if (body.destination_hash && body.destination_hash !== context.destinationHash) {
        return false;
    }
    if (body.file_path && body.file_path !== context.filePath) {
        return false;
    }
    return true;
}

export interface NomadImageLoaderDeps {
    getSelectedHash: () => string;
    getPagePath: () => string;
    isPrivate: () => boolean;
    getPerNodePolicy: (destinationHash: string) => string | undefined;
    getGlobalPolicy: () => unknown;
    setImage: (index: number, state: string, payload?: Record<string, unknown>) => void;
    chunkBuffers: NomadChunkBuffers;
}

/**
 * Nomad image loading for the crash-tab renderer. Tracks the image list the
 * frame reported, applies the effective load policy, downloads images over the
 * nomadnet file path, and pushes loaded/error state back into the frame.
 */
export class NomadImageLoader {
    images: NomadCrashTabImage[] = [];
    readonly cache = new Map<string, { dataUrl: string | null; size: string }>();
    callbacks: Record<number, NomadImageDownloadContext> = {};

    constructor(private deps: NomadImageLoaderDeps) {}

    policyFor(destinationHash?: string | null): NomadImagePolicy {
        const perNode = destinationHash ? this.deps.getPerNodePolicy(destinationHash) : undefined;
        return resolveNomadImagePolicy(perNode, this.deps.getGlobalPolicy());
    }

    autoLoads(destinationHash?: string | null): boolean {
        const policy = this.policyFor(destinationHash);
        return policy === "auto" || policy === "always";
    }

    onImages(images: unknown): void {
        this.images = Array.isArray(images) ? (images as NomadCrashTabImage[]) : [];
        this.cancelStaleDownloads();
        this.scheduleLoads();
    }

    onImageAction(payload: Record<string, unknown> | null | undefined): void {
        if (!payload || payload.action !== "load") {
            return;
        }
        const index = Number(payload.index);
        const image = this.images[index];
        if (!image) {
            return;
        }
        this.load(image, index);
    }

    scheduleLoads(): void {
        for (let i = 0; i < this.images.length; i++) {
            const image = this.images[i];
            const { destinationHash } = resolveNomadImageDestination(
                image?.path || image?.url,
                this.deps.getSelectedHash()
            );
            const policy = this.policyFor(destinationHash);
            if (policy === "auto" || policy === "always") {
                this.load(image, i);
            } else if (policy === "never") {
                this.deps.setImage(i, "error", { reason: t("nomadnet.image_policy_never") });
            }
        }
    }

    load(image: NomadCrashTabImage | null | undefined, index: number): void {
        if (!image || (!image.url && !image.path)) {
            return;
        }
        const { destinationHash, filePath } = resolveNomadImageDestination(
            image.path || image.url,
            this.deps.getSelectedHash()
        );
        if (!destinationHash || !filePath) {
            this.deps.setImage(index, "error", { reason: t("nomadnet.image_invalid_url") });
            return;
        }
        const cached = this.cache.get(nomadImageCacheKey(destinationHash, filePath));
        if (cached) {
            this.deps.setImage(index, "loaded", { dataUrl: cached.dataUrl, actualSize: cached.size });
            return;
        }
        if (this.callbacks[index]) {
            return;
        }
        this.deps.setImage(index, "loading");
        const requestId = generateNomadImageRequestId();
        const data: Record<string, unknown> = {
            image_id: index,
            request_id: requestId,
            page_path: this.deps.getPagePath(),
        };
        if (image.profile) {
            data.image_profile = image.profile;
        }
        const context: NomadImageDownloadContext = { destinationHash, filePath, requestId, downloadId: null };
        this.callbacks[index] = context;
        const payload = createNomadImageDownloadPayload(destinationHash, filePath, this.deps.isPrivate(), data);
        if (sendNomadWs(payload)) {
            // kept so resendInFlightDownloads() can re-issue this request
            // after a websocket reconnect
            context.payload = payload;
            context.sent = true;
            return;
        }
        delete this.callbacks[index];
        this.deps.setImage(index, "error", { reason: t("nomadnet.websocket_not_connected") });
    }

    /**
     * Consume a nomadnet.file.download ws event. Returns true when the event
     * was claimed by an in-flight image download so the page must not treat it
     * as a regular file download.
     */
    handleFileDownloadEvent(json: Record<string, unknown>): boolean {
        let body = (json.nomadnet_file_download || null) as Record<string, unknown> | null;
        const data = (body?.data || null) as Record<string, unknown> | null;
        const imageId = data?.image_id;
        if (imageId == null) {
            return false;
        }
        const downloadId = json.download_id as number | string | undefined;
        const context = this.callbacks[imageId as number];
        if (!context) {
            // A stale event for a cancelled download: claim it so it cannot
            // leak into the generic file-download handler, and drop any
            // buffered bytes the backend already streamed.
            discardDownloadChunks(this.deps.chunkBuffers, downloadId);
            return true;
        }
        if (!ownsNomadImageDownloadEvent(context, body, json)) {
            return true;
        }
        if (body!.status === "chunk") {
            appendDownloadChunk(this.deps.chunkBuffers, downloadId, body);
            return true;
        }
        if (body!.status === "success" && body!.chunked) {
            body = { ...body, file_bytes: consumeDownloadChunksAsBase64(this.deps.chunkBuffers, downloadId) };
        }
        if (body!.status === "started") {
            context.downloadId = downloadId ?? null;
            return true;
        }
        if (body!.status === "success") {
            this.onDownloadSuccess(imageId as number, body!.file_bytes as string);
            return true;
        }
        if (body!.status === "failure") {
            this.onDownloadFailure(imageId as number, body!.failure_reason as string);
            return true;
        }
        if (body!.status === "progress") {
            this.deps.setImage(imageId as number, "loading", { progress: body!.progress });
        }
        return true;
    }

    private onDownloadSuccess(imageId: number, fileBytes: string): void {
        const entry = this.callbacks[imageId];
        if (!entry) {
            return;
        }
        delete this.callbacks[imageId];
        if (!this.images[imageId]) {
            return;
        }
        const dataUrl = getNomadImageDataUrl(fileBytes);
        if (!dataUrl) {
            // A success with empty bytes is not loadable; report failure
            // instead of caching a null dataUrl as a permanent "loaded" hit.
            this.deps.setImage(imageId, "error", { reason: t("nomadnet.image_load_failed") });
            return;
        }
        const actualSize = formatBytes(fileBytes ? Math.ceil(fileBytes.length * 0.75) : 0);
        if (!this.deps.isPrivate()) {
            setNomadImageCacheEntry(
                this.cache,
                nomadImageCacheKey(entry.destinationHash, entry.filePath),
                { dataUrl, size: actualSize },
                false
            );
        }
        this.deps.setImage(imageId, "loaded", { dataUrl, actualSize });
    }

    private onDownloadFailure(imageId: number, reason: unknown): void {
        const context = this.callbacks[imageId];
        if (context) {
            discardDownloadChunks(this.deps.chunkBuffers, context.downloadId);
        }
        delete this.callbacks[imageId];
        this.deps.setImage(imageId, "error", {
            reason: typeof reason === "string" && reason ? reason : t("nomadnet.image_load_failed"),
        });
    }

    /** Re-issue in-flight image downloads after a websocket reconnect. */
    resendInFlightDownloads(): void {
        resendInFlightDownloadRequests(this.callbacks, this.deps.chunkBuffers, (index) => {
            this.deps.setImage(index, "error", { reason: t("nomadnet.websocket_not_connected") });
        });
    }

    cancelStaleDownloads(): void {
        for (const key of Object.keys(this.callbacks)) {
            const context = this.callbacks[key as unknown as number];
            if (context && context.downloadId != null) {
                sendNomadWs({
                    type: "nomadnet.download.cancel",
                    download_id: context.downloadId,
                    request_id: context.requestId,
                });
                discardDownloadChunks(this.deps.chunkBuffers, context.downloadId);
            }
            delete this.callbacks[key as unknown as number];
        }
    }

    /** Per-node policies stay in memory only so private sessions never leak. */
    clear(): void {
        this.cancelStaleDownloads();
        this.cache.clear();
        this.images = [];
    }
}
