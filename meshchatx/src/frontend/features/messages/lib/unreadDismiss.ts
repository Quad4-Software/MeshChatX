// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import type { Conversation, Pane, Peer } from "./types.js";

export type UnreadTarget = Conversation | Peer;

/**
 * Unique normalized destination hashes for open panes (dismissUnreadForVisiblePanes).
 */
export function collectOpenPaneDestinationHashes(panes: Pane[] | null | undefined): string[] {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const pane of panes || []) {
        const normalized = Utils.normalizeMeshchatHashHex(pane?.peer?.destination_hash || "");
        if (!normalized || seen.has(normalized)) {
            continue;
        }
        seen.add(normalized);
        out.push(normalized);
    }
    return out;
}

/**
 * Find a conversation or fall back to a matching pane peer / selected peer.
 */
export function findUnreadTarget(
    destinationHash: string | null | undefined,
    conversations: Conversation[] | null | undefined,
    panes: Pane[] | null | undefined,
    selectedPeer?: Peer | null
): UnreadTarget | null {
    const normalized = Utils.normalizeMeshchatHashHex(destinationHash || "");
    if (!normalized) {
        return null;
    }
    const fromList = (conversations || []).find(
        (c) => Utils.normalizeMeshchatHashHex(c.destination_hash) === normalized
    );
    if (fromList) {
        return fromList;
    }
    const fromPane = (panes || []).find(
        (p) => Utils.normalizeMeshchatHashHex(p?.peer?.destination_hash) === normalized
    )?.peer;
    if (fromPane) {
        return fromPane;
    }
    if (selectedPeer && Utils.normalizeMeshchatHashHex(selectedPeer.destination_hash) === normalized) {
        return selectedPeer;
    }
    return null;
}

/**
 * Whether dismissUnread should run for this target.
 */
export function shouldDismissUnread(target: UnreadTarget | null | undefined, force = false): boolean {
    if (!target) {
        return false;
    }
    if (force) {
        return true;
    }
    return target.is_unread === true;
}

/**
 * Destinations among open panes that should clear unread.
 */
export function destinationsNeedingUnreadDismiss(
    panes: Pane[] | null | undefined,
    conversations: Conversation[] | null | undefined,
    force = false
): string[] {
    const hashes = collectOpenPaneDestinationHashes(panes);
    const out: string[] = [];
    for (const normalized of hashes) {
        const conversation =
            (conversations || []).find((c) => Utils.normalizeMeshchatHashHex(c.destination_hash) === normalized) ||
            (panes || []).find((p) => Utils.normalizeMeshchatHashHex(p?.peer?.destination_hash) === normalized)?.peer;
        if (!shouldDismissUnread(conversation, force)) {
            continue;
        }
        out.push(normalized);
    }
    return out;
}

/**
 * Optimistically clear is_unread on a local conversation/peer object.
 * Returns whether it was unread before (for counter / rollback).
 * API / GlobalState / viewer mark-as-read stay in the page layer.
 */
export function applyOptimisticUnreadClear(target: UnreadTarget | null | undefined): boolean {
    if (!target) {
        return false;
    }
    const wasUnread = target.is_unread === true;
    if (wasUnread) {
        target.is_unread = false;
    }
    return wasUnread;
}

/**
 * Restore is_unread after a failed mark-as-read.
 */
export function revertOptimisticUnreadClear(target: UnreadTarget | null | undefined, wasUnread: boolean): void {
    if (!target || !wasUnread) {
        return;
    }
    target.is_unread = true;
}

/**
 * Next GlobalState.unreadConversationsCount after a successful mark-as-read.
 */
export function nextUnreadConversationsCount(current: number, wasUnread: boolean): number {
    if (!wasUnread) {
        return current;
    }
    if (typeof current !== "number" || current <= 0) {
        return 0;
    }
    return current - 1;
}
