// SPDX-License-Identifier: 0BSD

/**
 * Build a compact signature for a conversation list page.
 * Used to skip redundant sidebar refreshes when polling returns unchanged data.
 *
 * @param {Array<{ destination_hash?: string, updated_at?: string, is_unread?: boolean, failed_messages_count?: number, latest_message_created_at?: number | string | null }>} conversations
 * @returns {string}
 */
export function conversationListSignature(conversations) {
    if (!Array.isArray(conversations) || conversations.length === 0) {
        return "";
    }
    return conversations
        .map((conversation) => {
            const hash = conversation?.destination_hash || "";
            const updatedAt = conversation?.updated_at || "";
            const unread = conversation?.is_unread ? "1" : "0";
            const failed = conversation?.failed_messages_count ?? 0;
            const latest = conversation?.latest_message_created_at ?? "";
            const preview = conversation?.latest_message_preview || "";
            return `${hash}\u241f${updatedAt}\u241f${unread}\u241f${failed}\u241f${latest}\u241f${preview}`;
        })
        .join("\u241e");
}

/**
 * Count unread conversations in a list.
 *
 * @param {Array<{ is_unread?: boolean }>} conversations
 * @returns {number}
 */
export function countUnreadConversations(conversations) {
    if (!Array.isArray(conversations)) {
        return 0;
    }
    let count = 0;
    for (const conversation of conversations) {
        if (conversation?.is_unread) {
            count += 1;
        }
    }
    return count;
}

/**
 * Apply a refreshed conversation page in place, preserving row object identity when possible.
 *
 * @param {Array<object>} existing
 * @param {Array<object>} incoming
 * @returns {boolean} true when any visible list state changed
 */
export function syncConversationListInPlace(existing, incoming) {
    if (!Array.isArray(existing) || !Array.isArray(incoming)) {
        return false;
    }
    if (incoming.length === 0) {
        if (existing.length === 0) {
            return false;
        }
        existing.length = 0;
        return true;
    }
    if (existing.length === 0) {
        existing.push(...incoming);
        return true;
    }

    const existingByHash = new Map(existing.map((conversation) => [conversation.destination_hash, conversation]));
    const nextRows = [];
    for (const conversation of incoming) {
        const hash = conversation?.destination_hash;
        if (!hash) {
            continue;
        }
        const previous = existingByHash.get(hash);
        if (previous) {
            Object.assign(previous, conversation);
            nextRows.push(previous);
        } else {
            nextRows.push(conversation);
        }
    }

    const sameOrderAndRefs =
        nextRows.length === existing.length && nextRows.every((row, index) => row === existing[index]);
    if (sameOrderAndRefs) {
        return false;
    }

    existing.length = 0;
    existing.push(...nextRows);
    return true;
}
