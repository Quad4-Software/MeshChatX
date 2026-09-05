// SPDX-License-Identifier: 0BSD

import { lxmfConversationListPreview } from "../../../js/lxmfConversationPreview.js";
import { ANONYMOUS_PEER_DISPLAY_NAME } from "./peerAnnounce.js";
import type { Conversation, Peer } from "./types.js";

export type LxmfMessageLike = {
    is_incoming?: boolean;
    source_hash?: string;
    destination_hash?: string;
    content?: string;
    title?: string;
    fields?: Record<string, unknown>;
    hash?: string;
    timestamp?: number;
    state?: string | null;
    [key: string]: unknown;
};

export type ComposeEnqueuePayload = {
    peerHash: string;
    previewText?: string;
    title?: string;
    fields?: Record<string, unknown>;
    pendingHash?: string;
};

export type PreviewContext = {
    myLxmfAddressHash?: string;
    peerDisplayName: string;
    t?: (key: string, values?: Record<string, unknown>) => string;
};

/**
 * Peer hash for an LXMF message row (MessagesPage peerHashFromMessage).
 */
export function peerHashFromMessage(msg: LxmfMessageLike | null | undefined): string | null {
    if (!msg) {
        return null;
    }
    return msg.is_incoming ? (msg.source_hash ?? null) : (msg.destination_hash ?? null);
}

/**
 * Sidebar display name for a peer from conversations then peers map.
 */
export function peerDisplayNameForConversationSidebar(
    peerHash: string,
    conversations: Conversation[] | null | undefined,
    peers: Record<string, Peer> | null | undefined
): string {
    const conv = (conversations || []).find((c) => c.destination_hash === peerHash);
    if (conv) {
        return conv.custom_display_name ?? conv.display_name ?? ANONYMOUS_PEER_DISPLAY_NAME;
    }
    const peer = peers?.[peerHash];
    return peer?.custom_display_name ?? peer?.display_name ?? ANONYMOUS_PEER_DISPLAY_NAME;
}

/**
 * Adjust failed_messages_count when outbound message state changes.
 */
export function nextFailedMessagesCount(
    currentCount: number | null | undefined,
    oldState: string | null | undefined,
    newState: string | null | undefined
): number {
    let count = typeof currentCount === "number" ? currentCount : 0;
    if (newState === "failed" && oldState !== "failed") {
        return count + 1;
    }
    if (oldState === "failed" && newState !== "failed") {
        return Math.max(0, (count || 1) - 1);
    }
    return count;
}

/**
 * Mutate conversation failed count + _lastKnownState from lxmf_message_state_updated.
 * Returns false when conversation is missing.
 */
export function applyFailedCountFromStateUpdate(
    conversation: Conversation | null | undefined,
    msg: LxmfMessageLike | null | undefined
): boolean {
    if (!conversation || !msg) {
        return false;
    }
    const oldState = conversation._lastKnownState;
    const newState = msg.state ?? null;
    conversation._lastKnownState = newState;
    conversation.failed_messages_count = nextFailedMessagesCount(
        conversation.failed_messages_count,
        oldState,
        newState
    );
    return true;
}

export type ApplyPreviewInput = {
    conversations: Conversation[];
    peerHash: string;
    preview: string;
    title?: string | null;
    timestampSec: number;
    peers?: Record<string, Peer> | null;
    selectedPeer?: Peer | null;
};

/**
 * Optimistic sidebar bump for outbound compose enqueue or lxmf_message_created.
 * Mutates conversations in place (Vue array). Returns "updated" | "created".
 */
export function applyOutboundPreviewToConversations(input: ApplyPreviewInput): "updated" | "created" {
    const { conversations, peerHash, preview, title, timestampSec, peers, selectedPeer } = input;
    const updatedAt = new Date(timestampSec * 1000).toISOString();
    const idx = conversations.findIndex((c) => c.destination_hash === peerHash);
    if (idx !== -1) {
        const conv = conversations[idx];
        conv.latest_message_preview = preview;
        conv.latest_message_title = title ?? "";
        conv.latest_message_created_at = timestampSec;
        conv.updated_at = updatedAt;
        return "updated";
    }

    const peer = peers?.[peerHash];
    conversations.unshift({
        destination_hash: peerHash,
        display_name: peer?.display_name ?? selectedPeer?.display_name ?? ANONYMOUS_PEER_DISPLAY_NAME,
        custom_display_name: peer?.custom_display_name ?? selectedPeer?.custom_display_name ?? null,
        contact_image: peer?.contact_image ?? null,
        lxmf_user_icon: peer?.lxmf_user_icon ?? null,
        is_unread: false,
        is_tracking: peer?.is_tracking ?? false,
        failed_messages_count: 0,
        has_attachments: false,
        latest_message_preview: preview,
        latest_message_title: title ?? "",
        latest_message_created_at: timestampSec,
        updated_at: updatedAt,
        is_contact: false,
    });
    return "created";
}

/**
 * Build preview text + apply outbound compose enqueue stub to the conversation list.
 */
export function applyOutboundComposeEnqueued(
    conversations: Conversation[],
    payload: ComposeEnqueuePayload,
    ctx: {
        peers?: Record<string, Peer> | null;
        selectedPeer?: Peer | null;
        myLxmfAddressHash?: string;
        t?: PreviewContext["t"];
    }
): "updated" | "created" | null {
    if (!payload?.peerHash) {
        return null;
    }
    const peerHash = payload.peerHash;
    const nowSec = Math.floor(Date.now() / 1000);
    const stub: LxmfMessageLike = {
        content: payload.previewText || "",
        title: payload.title || "",
        fields: payload.fields || {},
        hash: payload.pendingHash || "",
        timestamp: nowSec,
        is_incoming: false,
    };
    const peerDisplay = peerDisplayNameForConversationSidebar(peerHash, conversations, ctx.peers ?? null);
    const preview = lxmfConversationListPreview(stub, {
        myLxmfAddressHash: ctx.myLxmfAddressHash || "",
        peerDisplayName: peerDisplay,
        t: ctx.t,
    });
    return applyOutboundPreviewToConversations({
        conversations,
        peerHash,
        preview,
        title: stub.title,
        timestampSec: nowSec,
        peers: ctx.peers,
        selectedPeer: ctx.selectedPeer,
    });
}

/**
 * Apply lxmf_message_created preview bump to the conversation list.
 */
export function applyOutboundMessageCreated(
    conversations: Conversation[],
    msg: LxmfMessageLike,
    ctx: {
        peers?: Record<string, Peer> | null;
        selectedPeer?: Peer | null;
        myLxmfAddressHash?: string;
        t?: PreviewContext["t"];
    }
): "updated" | "created" | null {
    const peerHash = peerHashFromMessage(msg);
    if (!peerHash) {
        return null;
    }
    const peerDisplay = peerDisplayNameForConversationSidebar(peerHash, conversations, ctx.peers ?? null);
    const preview = lxmfConversationListPreview(msg, {
        myLxmfAddressHash: ctx.myLxmfAddressHash || "",
        peerDisplayName: peerDisplay,
        t: ctx.t,
    });
    const timestampSec = typeof msg.timestamp === "number" ? msg.timestamp : Math.floor(Date.now() / 1000);
    return applyOutboundPreviewToConversations({
        conversations,
        peerHash,
        preview,
        title: msg.title,
        timestampSec,
        peers: ctx.peers,
        selectedPeer: ctx.selectedPeer,
    });
}

/**
 * Apply lxmf_message_state_updated failed-count logic for a peer hash.
 */
export function applyOutboundMessageStateUpdated(conversations: Conversation[], msg: LxmfMessageLike): boolean {
    const peerHash = peerHashFromMessage(msg);
    if (!peerHash) {
        return false;
    }
    const conv = conversations.find((c) => c.destination_hash === peerHash);
    return applyFailedCountFromStateUpdate(conv, msg);
}
