// SPDX-License-Identifier: 0BSD

import { ANONYMOUS_PEER_DISPLAY_NAME } from "./constants.js";
import type { Conversation, Peer } from "./types.js";

export { ANONYMOUS_PEER_DISPLAY_NAME };

export function preferKnownDisplayName(
    incomingName: string | null | undefined,
    existingName: string | null | undefined
): string | null | undefined {
    if (incomingName === ANONYMOUS_PEER_DISPLAY_NAME && existingName && existingName !== ANONYMOUS_PEER_DISPLAY_NAME) {
        return existingName;
    }
    return incomingName;
}

/**
 * Merge announce fields into an existing peer without wiping a known display_name.
 */
export function mergePeerFromAnnounce(existing: Peer | null | undefined, announce: Peer): Peer {
    const base = existing && typeof existing === "object" ? existing : {};
    const merged: Peer = { ...base, ...announce };
    const kept = preferKnownDisplayName(announce?.display_name, (base as Peer).display_name);
    if (kept !== undefined) {
        merged.display_name = kept;
    }
    return merged;
}

/**
 * Merge conversation list row into an existing peers map entry (getConversations loop).
 */
export function mergePeerFromConversation(existing: Peer | null | undefined, conversation: Conversation): Peer {
    const base = existing && typeof existing === "object" ? existing : {};
    const displayName = preferKnownDisplayName(
        conversation.display_name ?? (base as Peer).display_name,
        (base as Peer).display_name
    );
    return {
        ...base,
        destination_hash: conversation.destination_hash,
        display_name: displayName,
        custom_display_name: conversation.custom_display_name ?? (base as Peer).custom_display_name,
        contact_image: conversation.contact_image ?? (base as Peer).contact_image,
        lxmf_user_icon: conversation.lxmf_user_icon ?? (base as Peer).lxmf_user_icon,
        updated_at: conversation.updated_at ?? (base as Peer).updated_at,
        is_tracking: conversation.is_tracking ?? (base as Peer).is_tracking,
    };
}

/**
 * Apply announce merge into a peers map keyed by destination_hash. Mutates map (Vue-friendly).
 */
export function updatePeerFromAnnounce(peers: Record<string, Peer>, announce: Peer | null | undefined): Peer | null {
    if (!announce?.destination_hash || !peers || typeof peers !== "object") {
        return null;
    }
    const existing = peers[announce.destination_hash] || {};
    const merged = mergePeerFromAnnounce(existing, announce);
    peers[announce.destination_hash] = merged;
    return merged;
}

/**
 * Apply conversation-row merge into a peers map. Mutates map (Vue-friendly).
 */
export function updatePeerFromConversation(
    peers: Record<string, Peer>,
    conversation: Conversation | null | undefined
): Peer | null {
    if (!conversation?.destination_hash || !peers || typeof peers !== "object") {
        return null;
    }
    const existing = peers[conversation.destination_hash] || {};
    const merged = mergePeerFromConversation(existing, conversation);
    peers[conversation.destination_hash] = merged;
    return merged;
}

/**
 * Whether a resolved conversation/peer display_name should replace a pane peer name.
 */
export function shouldUpdatePanePeerDisplayName(
    incomingName: string | null | undefined,
    currentName: string | null | undefined
): boolean {
    return Boolean(incomingName && incomingName !== ANONYMOUS_PEER_DISPLAY_NAME && incomingName !== currentName);
}
