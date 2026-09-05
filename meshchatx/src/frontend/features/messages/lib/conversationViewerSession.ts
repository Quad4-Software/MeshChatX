// SPDX-License-Identifier: 0BSD

import GlobalEmitter from "../../../js/GlobalEmitter.js";
import GlobalState from "../../../js/GlobalState.js";
import NotificationUtils from "../../../js/NotificationUtils.js";
import { fromNow } from "../../../libs/datetime.js";
import { isTelemetryOnly } from "./conversationMessageHelpers.js";
import {
    fetchConversationPage,
    oldestMessageId,
    prependConversationPage,
} from "./conversationViewerMessages.js";
import type { LxmfMessage, ViewerChatItem } from "./conversationViewerCtx.js";
import { sameHash } from "./conversationViewerCtx.js";
import type { ApiClient } from "../../../js/apiClient.js";
import type { Conversation, Peer } from "./types.js";

export async function markConversationAsRead(
    api: ApiClient,
    conversation: (Conversation | Peer | { destination_hash?: string; is_unread?: boolean }) | null | undefined,
    opts: { force?: boolean } = {}
): Promise<boolean> {
    if (!conversation?.destination_hash) {
        return false;
    }
    const wasUnread = Boolean(conversation.is_unread);
    if (!wasUnread && !opts.force) {
        return false;
    }
    conversation.is_unread = false;
    try {
        await api.post(`/api/v1/lxmf/conversations/${conversation.destination_hash}/mark-as-read`);
        GlobalEmitter.emit("notifications-changed");
        NotificationUtils.clearMessageNotifications(conversation.destination_hash);
        if (wasUnread && GlobalState.unreadConversationsCount > 0) {
            GlobalState.unreadConversationsCount -= 1;
        }
        return true;
    } catch {
        conversation.is_unread = wasUnread;
        return false;
    }
}

export async function fetchTelephoneContacts(api: ApiClient): Promise<Array<Record<string, unknown>>> {
    try {
        const response = await api.get("/api/v1/telephone/contacts");
        const resData = response.data as { contacts?: unknown[] } | unknown[] | undefined;
        if (resData && !Array.isArray(resData) && Array.isArray(resData.contacts)) {
            return resData.contacts as Array<Record<string, unknown>>;
        }
        if (Array.isArray(resData)) {
            return resData as Array<Record<string, unknown>>;
        }
        return [];
    } catch {
        return [];
    }
}

export function filterContactsList(
    contacts: Array<Record<string, unknown>>,
    searchQuery: string
): Array<Record<string, unknown>> {
    const q = searchQuery.trim().toLowerCase();
    if (!q) {
        return contacts;
    }
    return contacts.filter((contact) => {
        const name = String(contact.name || "").toLowerCase();
        const hash = String(contact.remote_identity_hash || "").toLowerCase();
        const lxmf = String(contact.lxmf_address || "").toLowerCase();
        return name.includes(q) || hash.includes(q) || lxmf.includes(q);
    });
}

export function filterSelectedPeerTelemetry(
    chatItems: ViewerChatItem[],
    selectedHash: string
): ViewerChatItem[] {
    if (!selectedHash) {
        return [];
    }
    const peer = selectedHash.toLowerCase();
    return chatItems
        .filter((chatItem) => {
            if (chatItem.type !== "lxmf_message") {
                return false;
            }
            const src = String(chatItem.lxmf_message.source_hash || "").toLowerCase();
            const dst = String(chatItem.lxmf_message.destination_hash || "").toLowerCase();
            if (src !== peer && dst !== peer) {
                return false;
            }
            return isTelemetryOnly(chatItem.lxmf_message);
        })
        .slice()
        .reverse();
}

export type ComposeSuggestion = {
    hash: string;
    name: string;
    icon: string;
    type: string;
};

export function buildComposeAddressSuggestions(
    contacts: Array<Record<string, unknown>>,
    conversations: Conversation[],
    composeAddress: string,
    isInputFocused: boolean
): ComposeSuggestion[] {
    if (!isInputFocused) {
        return [];
    }
    const search = composeAddress.trim().toLowerCase();
    const seen: string[] = [];
    const suggestions: ComposeSuggestion[] = [];
    for (const contact of contacts) {
        const hash = String(contact.remote_identity_hash || "");
        const name = String(contact.name || hash);
        if (
            hash &&
            !seen.includes(hash) &&
            (!search || name.toLowerCase().includes(search) || hash.includes(search))
        ) {
            suggestions.push({ hash, name, icon: "account", type: "contact" });
            seen.push(hash);
        }
    }
    for (const conversation of conversations) {
        const hash = String(conversation.destination_hash || "");
        const name = String(conversation.custom_display_name || conversation.display_name || hash);
        if (
            hash &&
            !seen.includes(hash) &&
            (!search || name.toLowerCase().includes(search) || hash.includes(search))
        ) {
            suggestions.push({ hash, name, icon: "history", type: "recent" });
            seen.push(hash);
        }
    }
    return suggestions.slice(0, 10);
}

export function formatTimeAgo(value: unknown): string {
    return value ? fromNow(value as string) : "";
}

export function isPeerBlockedInState(blockedList: unknown, targetHash: string): boolean {
    if (!Array.isArray(blockedList) || !targetHash) {
        return false;
    }
    return blockedList.some((entry: unknown) => {
        const hash =
            typeof entry === "string"
                ? entry
                : String((entry as Record<string, unknown>)?.destination_hash || "");
        return sameHash(hash, targetHash);
    });
}


export type OpenConversationSeed = {
    chatItems: ViewerChatItem[];
    hasMorePrevious: boolean;
    autoScrollOnNewMessage: boolean;
    messagesViewportReady: boolean;
    peerPathSnapshot: null;
    selectedPeerLxmfStampInfo: null;
    selectedPeerSignalMetrics: null;
    strangerBannerDismissed: boolean;
    newMessageText: string;
    isStrangerPeer: boolean;
};

export function prepareOpenConversationState(opts: {
    peerHash: string;
    nextIdentity: string;
    contacts: Array<Record<string, unknown>>;
    loadDraft: (peerHash: string, identity: string) => string;
}): OpenConversationSeed {
    const { peerHash, nextIdentity, contacts, loadDraft } = opts;
    return {
        chatItems: [],
        hasMorePrevious: true,
        autoScrollOnNewMessage: true,
        messagesViewportReady: !peerHash,
        peerPathSnapshot: null,
        selectedPeerLxmfStampInfo: null,
        selectedPeerSignalMetrics: null,
        strangerBannerDismissed: false,
        newMessageText: peerHash ? loadDraft(peerHash, nextIdentity) : "",
        isStrangerPeer: Boolean(peerHash) && !contacts.some((c) => sameHash(c.remote_identity_hash, peerHash)),
    };
}


export async function runLoadPreviousPage(opts: {
    api: ApiClient;
    peerHash: string;
    myLxmfAddressHash: string;
    chatItems: ViewerChatItem[];
    requestSequence: number;
    currentSelectedHash: string;
    messagesScroll: HTMLElement | null | undefined;
    tick: () => Promise<void>;
}): Promise<{ items: ViewerChatItem[]; hasMorePrevious: boolean } | null> {
    const {
        api,
        peerHash,
        myLxmfAddressHash,
        chatItems,
        requestSequence,
        currentSelectedHash,
        messagesScroll,
        tick,
    } = opts;
    const anchorHeight = messagesScroll?.scrollHeight || 0;
    const anchorTop = messagesScroll?.scrollTop || 0;
    try {
        const page = await fetchConversationPage(
            api,
            peerHash,
            myLxmfAddressHash,
            oldestMessageId(chatItems, peerHash)
        );
        if (!sameHash(peerHash, currentSelectedHash)) {
            return null;
        }
        const merged = prependConversationPage(chatItems, page.items);
        await tick();
        if (messagesScroll && anchorHeight > 0) {
            messagesScroll.scrollTop = anchorTop + messagesScroll.scrollHeight - anchorHeight;
        }
        return {
            items: merged.items,
            hasMorePrevious: page.hasMore && merged.added > 0,
        };
    } catch {
        return { items: chatItems, hasMorePrevious: false };
    }
}
