// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import DownloadUtils from "../../../js/DownloadUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import Utils from "../../../js/Utils.js";
import WebSocketConnection from "../../../js/WebSocketConnection.js";
import { copyImageBlobToClipboard } from "../../../js/clipboardUtils.js";
import { t } from "../../../js/i18n.js";
import { applyWsMessage, deleteWsMessage, updateWsMessage } from "./conversationViewerMessages.js";
import { cancelOutbound, executeOutboundJob, type OutboundJob } from "./conversationViewerSend.js";
import type { ApiClient } from "../../../js/apiClient.js";
import type { LxmfMessage, ViewerChatItem } from "./conversationViewerCtx.js";
import type { MessageChatItem } from "./viewerActions.js";

function base64ToArrayBuffer(base64: string): Uint8Array {
    return Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
}

function sameHash(a: unknown, b: unknown): boolean {
    return String(a || "").toLowerCase() === String(b || "").toLowerCase();
}

export function listFailedOrCancelledOutbound(items: ViewerChatItem[] | null | undefined): ViewerChatItem[] {
    return (items || []).filter(
        (item) => item.is_outbound && ["failed", "cancelled"].includes(String(item.lxmf_message?.state || ""))
    );
}

export async function resolveMessageImageBlob(
    api: ApiClient,
    item: ViewerChatItem | MessageChatItem | null | undefined
): Promise<Blob | null> {
    const msg = item?.lxmf_message;
    const img = msg?.fields?.image as { image_type?: string; image_bytes?: string } | undefined;
    if (!msg?.hash || !img) {
        return null;
    }
    const rawType = String(img.image_type || "png")
        .replace(/^image\//, "")
        .toLowerCase();
    const mimeExt = rawType === "jpg" ? "jpeg" : rawType || "png";
    const mime = `image/${mimeExt}`;
    if (img.image_bytes) {
        return new Blob([base64ToArrayBuffer(img.image_bytes).buffer as ArrayBuffer], { type: mime });
    }
    const response = await api.get(`/api/v1/lxmf-messages/attachment/${msg.hash}/image`, {
        responseType: "arraybuffer",
    });
    const headers = (response as unknown as { headers?: Record<string, string> })?.headers || {};
    const headerType = headers["content-type"] || headers["Content-Type"];
    const type = typeof headerType === "string" && headerType.startsWith("image/") ? headerType.split(";")[0] : mime;
    return new Blob([response.data as ArrayBuffer], { type });
}

export async function copyMessageImageToClipboard(
    api: ApiClient,
    item: ViewerChatItem | MessageChatItem | null | undefined
): Promise<boolean> {
    try {
        const blob = await resolveMessageImageBlob(api, item);
        if (!blob) {
            return false;
        }
        const ok = await copyImageBlobToClipboard(blob);
        if (!ok) {
            ToastUtils.error(t("messages.clipboard_write_unavailable"));
            return false;
        }
        ToastUtils.success(t("messages.image_copied_to_clipboard"));
        return true;
    } catch {
        ToastUtils.error(t("common.error"));
        return false;
    }
}

async function resolveImageBytesBase64(
    api: ApiClient,
    msg: LxmfMessage | Record<string, unknown>
): Promise<{ b64: string; imageType: string } | null> {
    const fields = msg.fields as { image?: { image_type?: string; image_bytes?: string } } | undefined;
    const img = fields?.image;
    if (!img) {
        return null;
    }
    let b64 = img.image_bytes || "";
    if (!b64) {
        const res = await api.get(`/api/v1/lxmf-messages/attachment/${String(msg.hash || "")}/image`, {
            responseType: "arraybuffer",
        });
        b64 = Utils.arrayBufferToBase64(res.data as ArrayBuffer);
    }
    const imageType = String(img.image_type || "png").replace(/^image\//, "");
    return { b64, imageType };
}

export async function saveMessageImageToStickers(
    api: ApiClient,
    item: ViewerChatItem | MessageChatItem | null | undefined
): Promise<void> {
    const msg = item?.lxmf_message;
    if (!msg) {
        return;
    }
    try {
        const resolved = await resolveImageBytesBase64(api, msg);
        if (!resolved) {
            return;
        }
        await api.post("/api/v1/stickers", {
            image_bytes: resolved.b64,
            image_type: resolved.imageType,
            source_message_hash: msg.hash,
            name: null,
        });
        ToastUtils.success(t("stickers.saved"));
    } catch (error) {
        const err = (error as { response?: { data?: { error?: string } } })?.response?.data?.error;
        if (err === "duplicate_sticker") {
            ToastUtils.info(t("stickers.duplicate"));
        } else {
            ToastUtils.error(t("stickers.save_failed"));
        }
    }
}

export async function saveMessageImageToGifs(
    api: ApiClient,
    item: ViewerChatItem | MessageChatItem | null | undefined
): Promise<void> {
    const msg = item?.lxmf_message;
    if (!msg) {
        return;
    }
    try {
        const resolved = await resolveImageBytesBase64(api, msg);
        if (!resolved) {
            return;
        }
        await api.post("/api/v1/gifs", {
            image_bytes: resolved.b64,
            image_type: resolved.imageType || "gif",
            source_message_hash: msg.hash,
            name: null,
        });
        ToastUtils.success(t("gifs.saved"));
    } catch (error) {
        const err = (error as { response?: { data?: { error?: string } } })?.response?.data?.error;
        if (err === "duplicate_gif") {
            ToastUtils.info(t("gifs.duplicate"));
        } else {
            ToastUtils.error(t("gifs.save_failed"));
        }
    }
}

/**
 * Delete then re-POST the original LXMF payload (preserves attachments and fields).
 */
export async function retryOutboundMessageItem(opts: {
    api: ApiClient;
    item: ViewerChatItem;
    currentItems: ViewerChatItem[];
    replyQuotedContent?: string | null;
}): Promise<ViewerChatItem[] | null> {
    const { api, item, currentItems, replyQuotedContent = null } = opts;
    const msg = item.lxmf_message;
    const hash = msg?.hash;
    if (!hash) {
        return null;
    }
    let next = currentItems;
    const deleted = await deleteMessageItem({ api, item, currentItems, skipConfirm: true });
    if (deleted) {
        next = deleted;
    }
    try {
        const response = await api.post(`/api/v1/lxmf-messages/send`, {
            lxmf_message: {
                destination_hash: msg.destination_hash,
                content: msg.content,
                reply_to_hash: msg.reply_to_hash || null,
                reply_quoted_content: replyQuotedContent || null,
                fields: msg.fields,
            },
        });
        const sent = (response.data as { lxmf_message?: LxmfMessage } | undefined)?.lxmf_message;
        if (sent?.hash && !next.some((candidate) => sameHash(candidate.lxmf_message.hash, sent.hash))) {
            next = next.concat({
                type: "lxmf_message",
                is_outbound: true,
                lxmf_message: sent,
            });
        }
        return next;
    } catch (error) {
        const message =
            (error as { response?: { data?: { message?: string } } }).response?.data?.message ||
            t("messages.failed_to_send");
        await DialogUtils.alert(message);
        return next;
    }
}

type OutboundQueueLike = {
    cancelJob: (predicate: { pendingHash?: string }) => void;
};

export async function sendReactionToMessage(opts: {
    api: ApiClient;
    destinationHash: string;
    myLxmfAddressHash: string;
    emoji: string;
    targetItem: ViewerChatItem;
    currentItems: ViewerChatItem[];
}): Promise<ViewerChatItem[]> {
    const { api, destinationHash, myLxmfAddressHash, emoji, targetItem, currentItems } = opts;
    const targetHash = targetItem.lxmf_message.hash;
    if (!targetHash || !destinationHash) {
        return currentItems;
    }
    try {
        const response = await api.post("/api/v1/lxmf-messages/reactions", {
            destination_hash: destinationHash,
            target_message_hash: targetHash,
            emoji,
        });
        const resData = response.data as { lxmf_message?: LxmfMessage } | undefined;
        const reaction = resData?.lxmf_message;
        if (reaction) {
            return applyWsMessage(currentItems, reaction, destinationHash, myLxmfAddressHash).items;
        }
        return currentItems;
    } catch {
        ToastUtils.error(t("messages.reaction_send_failed"));
        return currentItems;
    }
}

export async function deleteMessageItem(opts: {
    api: ApiClient;
    item: ViewerChatItem;
    currentItems: ViewerChatItem[];
    skipConfirm?: boolean;
}): Promise<ViewerChatItem[] | null> {
    const { api, item, currentItems, skipConfirm = false } = opts;
    const hash = item.lxmf_message.hash;
    if (!hash) {
        return null;
    }
    if (!skipConfirm) {
        const confirmed = await DialogUtils.confirm(t("messages.delete_message_confirm"));
        if (!confirmed) {
            return null;
        }
    }
    if (!hash.startsWith("pending-")) {
        try {
            await api.delete(`/api/v1/lxmf-messages/${hash}`);
        } catch {
            return null;
        }
    }
    return deleteWsMessage(currentItems, hash);
}

export async function cancelOutboundMessageItem(opts: {
    api: ApiClient;
    item: ViewerChatItem;
    currentItems: ViewerChatItem[];
    outboundQueue: OutboundQueueLike;
}): Promise<ViewerChatItem[]> {
    const { api, item, currentItems, outboundQueue } = opts;
    const hash = String(item.lxmf_message.hash || "");
    if (!hash) {
        return currentItems;
    }
    if (hash.startsWith("pending-")) {
        outboundQueue.cancelJob({ pendingHash: hash });
        return deleteWsMessage(currentItems, hash);
    }
    const updated = await cancelOutbound(api, hash);
    if (updated) {
        return updateWsMessage(currentItems, updated);
    }
    return currentItems;
}

export async function downloadMessageImageAttachment(api: ApiClient, item: MessageChatItem): Promise<void> {
    const hash = item.lxmf_message.hash;
    if (!hash) {
        return;
    }
    const response = await api.get(`/api/v1/lxmf-messages/attachment/${hash}/image`, {
        responseType: "arraybuffer",
    });
    const type = String(item.lxmf_message.fields?.image?.image_type || "png").replace(/^image\//, "");
    await DownloadUtils.downloadFromApiResponse(response, `image-${hash.slice(0, 8)}.${type}`);
}

export async function downloadMessageFileAttachment(
    api: ApiClient,
    item: ViewerChatItem,
    index: number,
    name: string
): Promise<void> {
    const hash = item.lxmf_message.hash;
    if (!hash) {
        return;
    }
    const response = await api.get(`/api/v1/lxmf-messages/attachment/${hash}/file`, {
        params: { file_index: index },
        responseType: "arraybuffer",
    });
    await DownloadUtils.downloadFromApiResponse(response, name || "download");
}

export async function updatePeerCustomDisplayName(
    api: ApiClient,
    destinationHash: string,
    onSuccess: (name: string) => void
): Promise<void> {
    if (!destinationHash) {
        return;
    }
    const displayName = await DialogUtils.prompt(t("messages.enter_display_name"));
    if (displayName == null) {
        return;
    }
    try {
        await api.post(`/api/v1/destination/${destinationHash}/custom-display-name/update`, {
            display_name: displayName,
        });
        onSuccess(displayName);
    } catch {
        await DialogUtils.alert(t("messages.failed_update_display_name"));
    }
}

export async function addStrangerContact(opts: {
    api: ApiClient;
    destinationHash: string;
    displayName?: string | null;
    identityHash?: string | null;
    onSuccess: () => void;
}): Promise<boolean> {
    const { api, destinationHash, displayName, identityHash, onSuccess } = opts;
    if (!destinationHash) {
        return false;
    }
    try {
        await api.post("/api/v1/telephone/contacts", {
            name: displayName || destinationHash,
            remote_identity_hash: String(identityHash || destinationHash),
            lxmf_address: destinationHash,
        });
        onSuccess();
        ToastUtils.success(t("contacts.contact_added"));
        return true;
    } catch {
        ToastUtils.error(t("messages.failed_add_contact"));
        return false;
    }
}

export async function addSharedContactEntry(opts: {
    api: ApiClient;
    name?: string;
    hash?: string;
    lxmfAddress?: string;
    lxstAddress?: string;
    onSuccess: () => void;
}): Promise<boolean> {
    const { api, name, hash, lxmfAddress, lxstAddress, onSuccess } = opts;
    const remoteHash = String(hash || "");
    if (!remoteHash) {
        return false;
    }
    try {
        await api.post("/api/v1/telephone/contacts", {
            name: name || remoteHash,
            remote_identity_hash: remoteHash,
            lxmf_address: lxmfAddress || remoteHash,
            lxst_address: lxstAddress || undefined,
        });
        onSuccess();
        ToastUtils.success(t("contacts.contact_added"));
        return true;
    } catch {
        ToastUtils.error(t("messages.failed_add_contact"));
        return false;
    }
}

export function generatePaperMessagePayload(destinationHash: string, text: string): void {
    if (!destinationHash || !text.trim()) {
        return;
    }
    WebSocketConnection.send(
        JSON.stringify({
            type: "lxm.generate_paper_uri",
            destination_hash: destinationHash,
            content: text,
        })
    );
}

export function formatSharedContactString(contact: Record<string, unknown>): string {
    let sharedString = `Contact: ${contact.name} <${contact.remote_identity_hash}>`;
    if (contact.lxmf_address) {
        sharedString += ` [LXMF: ${contact.lxmf_address}]`;
    }
    if (contact.lxst_address) {
        sharedString += ` [LXST: ${contact.lxst_address}]`;
    }
    return sharedString;
}

export function buildMapLocationHash(coords: { latitude: number; longitude: number }): string {
    const params = new URLSearchParams({
        lat: String(coords.latitude),
        lon: String(coords.longitude),
        zoom: "15",
    });
    return `#/map?${params.toString()}`;
}

export async function executeOutboundSendJob(opts: {
    api: ApiClient;
    job: OutboundJob;
    peerPathSnapshot: unknown;
    chatItems: ViewerChatItem[];
    myLxmfAddressHash: string;
    refreshPeerNetwork: (warm: boolean) => Promise<void>;
    DialogUtils: { alert: (message: string) => Promise<void> | void };
    t: (key: string) => string;
    applyWsMessage: typeof applyWsMessage;
    getPropagationHash: () => unknown;
}): Promise<ViewerChatItem[]> {
    const {
        api,
        job,
        peerPathSnapshot,
        chatItems,
        DialogUtils,
        t,
        applyWsMessage: applyMsg,
        refreshPeerNetwork,
        getPropagationHash,
    } = opts;
    try {
        const sent = await executeOutboundJob({
            api,
            job,
            pathSnapshot: peerPathSnapshot as never,
            propagationHash: getPropagationHash(),
        });
        let next = chatItems.filter((item) => item.lxmf_message.hash !== job.pendingHash);
        for (const message of sent) {
            next = applyMsg(next, message, job.destinationHash, job.myLxmfAddressHash).items;
        }
        void refreshPeerNetwork(false);
        return next;
    } catch (error) {
        const failed = chatItems.map((item) =>
            item.lxmf_message.hash === job.pendingHash
                ? {
                      ...item,
                      lxmf_message: {
                          ...item.lxmf_message,
                          state: "failed",
                          _pendingPathfinding: false,
                      },
                  }
                : item
        );
        await DialogUtils.alert(
            (error as { response?: { data?: { message?: string } } }).response?.data?.message ||
                t("messages.failed_to_send")
        );
        return failed;
    }
}
