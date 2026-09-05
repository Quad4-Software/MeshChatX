// SPDX-License-Identifier: 0BSD

import type { Conversation, MessagesConfig, Peer } from "./types.js";

export type LxmfFields = Record<string, unknown> & {
    image?: Record<string, unknown>;
    audio?: Record<string, unknown>;
    file_attachments?: Array<Record<string, unknown>>;
};

export type LxmfMessage = Record<string, unknown> & {
    id?: number;
    hash?: string;
    source_hash?: string;
    destination_hash?: string;
    content?: string;
    state?: string;
    timestamp?: number;
    created_at?: string;
    fields?: LxmfFields;
    is_reaction?: boolean;
    reaction_to?: string;
    reply_to_hash?: string | null;
};

export type ViewerChatItem = {
    type: "lxmf_message";
    is_outbound: boolean;
    lxmf_message: LxmfMessage;
};

export type ViewerPathSnapshot = Record<string, unknown> & {
    path?: {
        hops?: number;
        next_hop?: string;
        next_hop_interface?: string;
    } | null;
    path_stale?: boolean;
    path_unresponsive?: boolean;
};

export type ViewerState = {
    config: MessagesConfig | null;
    myLxmfAddressHash: string;
    selectedPeer: Peer | null;
    conversations: Conversation[];
    chatItems: ViewerChatItem[];
    hasMorePrevious: boolean;
    isLoadingPrevious: boolean;
    requestSequence: number;
};

export type ApiError = Error & {
    response?: {
        data?: { message?: string; diagnostics?: unknown };
        status?: number;
    };
};

export function sameHash(a: unknown, b: unknown): boolean {
    return String(a || "").toLowerCase() === String(b || "").toLowerCase();
}

export function messageKey(message: LxmfMessage): string {
    return String(message.hash || message.id || "");
}
