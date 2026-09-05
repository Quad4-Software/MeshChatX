// SPDX-License-Identifier: 0BSD

import type { Conversation } from "./types.js";

export function latestConversationCards(conversations: Conversation[], limit = 4) {
    return conversations
        .filter((conversation) => Boolean(conversation.destination_hash))
        .slice(0, limit)
        .map((conversation) => {
            const icon = (conversation as Record<string, unknown>).lxmf_user_icon;
            return {
                ...conversation,
                destination_hash: String(conversation.destination_hash),
                lxmf_user_icon: icon && typeof icon === "object" ? icon : null,
            };
        });
}

export function buildAudioAttachmentUrlMap(
    items: Array<{ lxmf_message: { hash?: string; fields?: { audio?: unknown } } }>
): Record<string, string> {
    return Object.fromEntries(
        items
            .filter((item) => item.lxmf_message.hash && item.lxmf_message.fields?.audio)
            .map((item) => [
                String(item.lxmf_message.hash),
                `/api/v1/lxmf-messages/attachment/${item.lxmf_message.hash}/audio`,
            ])
    );
}
