// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import DownloadUtils from "../../../js/DownloadUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import WebSocketConnection from "../../../js/WebSocketConnection.js";
import { t } from "../../../js/i18n.js";
import { applyWsMessage, deleteWsMessage, updateWsMessage } from "./conversationViewerMessages.js";
import { cancelOutbound, executeOutboundJob, type OutboundJob } from "./conversationViewerSend.js";
import type { ApiClient } from "../../../js/apiClient.js";
import type { LxmfMessage, ViewerChatItem } from "./conversationViewerCtx.js";
import type { MessageChatItem } from "./viewerActions.js";

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
