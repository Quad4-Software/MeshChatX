// SPDX-License-Identifier: 0BSD

import { mergeLxmfReactionRowsIntoMessages } from "../../../js/lxmfReactions.js";
import { CONVERSATION_MESSAGES_PAGE_SIZE } from "./conversationDisplayGroups.js";
import { hasRenderableContent, isTelemetryOnly } from "./conversationMessageHelpers.js";
import { normalizeLxmfMessage } from "./lxmf/normalize.js";
import type { LxmfMessage, ViewerChatItem } from "./conversationViewerCtx.js";
import { messageKey, sameHash } from "./conversationViewerCtx.js";

type ApiClient = {
    get: (url: string, options?: Record<string, unknown>) => Promise<{ data?: Record<string, unknown> }>;
};

export type ConversationPage = {
    items: ViewerChatItem[];
    hasMore: boolean;
};

function asMessages(value: unknown): LxmfMessage[] {
    return Array.isArray(value) ? (value as LxmfMessage[]) : [];
}

function toChatItem(message: LxmfMessage, myHash: string): ViewerChatItem {
    const outbound = Boolean(myHash) && sameHash(message.source_hash, myHash);
    return {
        type: "lxmf_message",
        is_outbound: outbound,
        lxmf_message: normalizeLxmfMessage(message, outbound) as LxmfMessage,
    };
}

export async function fetchConversationPage(
    api: ApiClient,
    peerHash: string,
    myHash: string,
    afterId: number | null
): Promise<ConversationPage> {
    const response = await api.get(`/api/v1/lxmf-messages/conversation/${peerHash}`, {
        params: {
            count: CONVERSATION_MESSAGES_PAGE_SIZE,
            order: "desc",
            after_id: afterId,
        },
    });
    const raw = asMessages(response.data?.lxmf_messages);
    const merged = mergeLxmfReactionRowsIntoMessages(raw) as LxmfMessage[];
    return {
        items: merged.map((message) => toChatItem(message, myHash)).reverse(),
        hasMore: raw.length >= CONVERSATION_MESSAGES_PAGE_SIZE,
    };
}

export function prependConversationPage(
    current: ViewerChatItem[],
    page: ViewerChatItem[]
): { items: ViewerChatItem[]; added: number } {
    const seen = new Set(current.map((item) => messageKey(item.lxmf_message)).filter(Boolean));
    const older = page.filter((item) => {
        const key = messageKey(item.lxmf_message);
        if (!key || seen.has(key)) {
            return false;
        }
        seen.add(key);
        return true;
    });
    return { items: older.concat(current), added: older.length };
}

export function oldestMessageId(items: ViewerChatItem[], peerHash: string): number | null {
    let oldest: number | null = null;
    for (const item of items) {
        const message = item.lxmf_message;
        if (!sameHash(message.source_hash, peerHash) && !sameHash(message.destination_hash, peerHash)) {
            continue;
        }
        if (typeof message.id === "number" && (oldest == null || message.id < oldest)) {
            oldest = message.id;
        }
    }
    return oldest;
}

export function visibleConversationItems(
    items: ViewerChatItem[],
    peerHash: string,
    showTelemetry: boolean
): ViewerChatItem[] {
    return items.filter((item) => {
        const message = item.lxmf_message;
        if (!sameHash(message.source_hash, peerHash) && !sameHash(message.destination_hash, peerHash)) {
            return false;
        }
        if (message.is_reaction) {
            return false;
        }
        if (!showTelemetry && isTelemetryOnly(message)) {
            return false;
        }
        return hasRenderableContent(message);
    });
}

export function applyWsMessage(
    current: ViewerChatItem[],
    message: LxmfMessage,
    peerHash: string,
    myHash: string
): { items: ViewerChatItem[]; changed: boolean; incoming: boolean } {
    const incoming = sameHash(message.source_hash, peerHash);
    const outbound = sameHash(message.destination_hash, peerHash) && sameHash(message.source_hash, myHash);
    if (!incoming && !outbound) {
        return { items: current, changed: false, incoming: false };
    }

    if (message.is_reaction && message.reaction_to) {
        const merged = mergeLxmfReactionRowsIntoMessages(
            current.map((item) => item.lxmf_message).concat(message)
        ) as LxmfMessage[];
        return {
            items: merged
                .filter((candidate) => !candidate.is_reaction)
                .map((candidate) => toChatItem(candidate, myHash)),
            changed: true,
            incoming,
        };
    }

    const index = current.findIndex((item) => sameHash(item.lxmf_message.hash, message.hash));
    if (index >= 0) {
        const items = current.slice();
        items[index] = {
            ...items[index],
            lxmf_message: { ...items[index].lxmf_message, ...message },
        };
        return { items, changed: true, incoming };
    }

    let items = current;
    if (outbound) {
        items = items.filter(
            (item) =>
                !(
                    String(item.lxmf_message.hash || "").startsWith("pending-") &&
                    sameHash(item.lxmf_message.destination_hash, peerHash)
                )
        );
    }
    return { items: items.concat(toChatItem(message, myHash)), changed: true, incoming };
}

export function updateWsMessage(current: ViewerChatItem[], message: LxmfMessage): ViewerChatItem[] {
    const index = current.findIndex((item) => sameHash(item.lxmf_message.hash, message.hash));
    if (index < 0) {
        return current;
    }
    const items = current.slice();
    items[index] = {
        ...items[index],
        lxmf_message: { ...items[index].lxmf_message, ...message },
    };
    return items;
}

export function deleteWsMessage(current: ViewerChatItem[], hash: unknown): ViewerChatItem[] {
    return current.filter((item) => !sameHash(item.lxmf_message.hash, hash));
}
