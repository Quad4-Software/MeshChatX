// SPDX-License-Identifier: 0BSD

import { loadMessagePanes, saveMessagePanes } from "../../../js/browserLayoutStore.js";
import type { Pane, Peer, PersistedPanePeer, PersistedPaneState } from "./types.js";

export type MaxPanesInput = {
    isPopoutMode?: boolean;
    isWideViewport?: boolean;
    multiPaneEnabled?: boolean;
    isWideEnoughForThreePanes?: boolean;
};

/**
 * Max concurrent conversation panes from viewport and config (MessagesPage maxPanes).
 */
export function maxPanesFromWidth(input: MaxPanesInput = {}): number {
    if (input.isPopoutMode || !input.isWideViewport || input.multiPaneEnabled === false) {
        return 1;
    }
    return input.isWideEnoughForThreePanes ? 3 : 2;
}

/**
 * Persistable peer slice for browserLayoutStore message panes.
 */
export function slimPeer(peer: Peer | null | undefined): PersistedPanePeer | null {
    if (!peer || !peer.destination_hash) {
        return null;
    }
    return {
        destination_hash: peer.destination_hash,
        display_name: peer.display_name ?? null,
        custom_display_name: peer.custom_display_name ?? null,
    };
}

/**
 * Signature used to watch layout changes and trigger persist.
 */
export function paneLayoutSignature(panes: Pane[], focusedPaneId: number): string {
    const hashes = (panes || []).map((pane) => pane.peer?.destination_hash || "").join("\u241f");
    const focusedIndex = (panes || []).findIndex((pane) => pane.id === focusedPaneId);
    return `${focusedIndex}\u241e${hashes}`;
}

export type VisiblePanesInput = {
    panes: Pane[];
    focusedPaneId: number;
    maxPanes: number;
};

/**
 * Which panes are shown given maxPanes and empty-pane filtering (MessagesPage visiblePanes).
 */
export function selectVisiblePanes(input: VisiblePanesInput): Pane[] {
    const panes = input.panes || [];
    const focused = panes.find((pane) => pane.id === input.focusedPaneId) || panes[0] || null;
    let visible: Pane[];
    if (input.maxPanes <= 1) {
        visible = focused ? [focused] : panes.slice(0, 1);
    } else {
        visible = panes.slice(0, input.maxPanes);
    }
    if (visible.length <= 1) {
        return visible;
    }
    const hasEmptyPane = visible.some((pane) => !pane.peer);
    if (!hasEmptyPane) {
        return visible;
    }
    return visible.filter((pane) => pane.peer || pane.id === input.focusedPaneId);
}

export function paneFlexValue(paneId: number, paneFlex: Record<number, number>, visiblePanes: Pane[]): number {
    if (!visiblePanes || visiblePanes.length <= 1) {
        return 1;
    }
    const pane = visiblePanes.find((entry) => entry.id === paneId);
    if (!pane?.peer) {
        return 1;
    }
    const value = paneFlex?.[paneId];
    return typeof value === "number" && value > 0 ? value : 1;
}

export type BuildPersistInput = {
    panes: Pane[];
    focusedPaneId: number;
    paneFlex: Record<number, number>;
    visiblePanes: Pane[];
};

/**
 * Pure shape for saveMessagePanes (no I/O).
 */
export function buildPersistedPaneState(input: BuildPersistInput): PersistedPaneState {
    const focusedIndex = (input.panes || []).findIndex((pane) => pane.id === input.focusedPaneId);
    return {
        panes: (input.panes || []).map((pane) => slimPeer(pane.peer)),
        sizes: (input.panes || []).map((pane) =>
            paneFlexValue(pane.id, input.paneFlex || {}, input.visiblePanes || [])
        ),
        focusedIndex: focusedIndex < 0 ? 0 : focusedIndex,
    };
}

export type RestorePanesResult = {
    panes: Pane[];
    paneFlex: Record<number, number>;
    focusedPaneId: number;
    nextPaneId: number;
};

/**
 * Pure restore from a saved layout into pane objects and flex map.
 * Caller supplies nextPaneId seed (MessagesPage starts at 2 after initial pane id 1).
 */
export function restorePanesFromSaved(
    saved: PersistedPaneState | null | undefined,
    routeHash: string | null | undefined,
    nextPaneIdSeed: number
): RestorePanesResult | null {
    if (!saved || !Array.isArray(saved.panes) || saved.panes.length === 0) {
        return null;
    }

    let nextPaneId = nextPaneIdSeed;
    const panes: Pane[] = saved.panes.map((peer) => ({
        id: nextPaneId++,
        peer: peer && peer.destination_hash ? { ...peer } : null,
    }));

    const paneFlex: Record<number, number> = {};
    panes.forEach((pane, index) => {
        const size = Array.isArray(saved.sizes) ? saved.sizes[index] : null;
        paneFlex[pane.id] = typeof size === "number" && size > 0 ? size : 1;
    });

    let focusedIndex =
        Number.isInteger(saved.focusedIndex) &&
        (saved.focusedIndex as number) >= 0 &&
        (saved.focusedIndex as number) < panes.length
            ? (saved.focusedIndex as number)
            : 0;
    let focusedPaneId = panes[focusedIndex].id;

    if (routeHash) {
        const match = panes.find((pane) => pane.peer?.destination_hash === routeHash);
        if (match) {
            focusedPaneId = match.id;
        }
    }

    return { panes, paneFlex, focusedPaneId, nextPaneId };
}

/**
 * Thin I/O wrapper around loadMessagePanes + restorePanesFromSaved.
 */
export function loadAndRestorePanes(
    routeHash: string | null | undefined,
    nextPaneIdSeed: number
): RestorePanesResult | null {
    return restorePanesFromSaved(loadMessagePanes() as PersistedPaneState | null, routeHash, nextPaneIdSeed);
}

/**
 * Thin I/O wrapper: build persist shape then saveMessagePanes.
 * sizes is persisted by MessagesPage even though the store JSDoc omits it.
 */
export function persistPanesState(input: BuildPersistInput): void {
    const state = buildPersistedPaneState(input);
    saveMessagePanes({
        panes: state.panes,
        focusedIndex: state.focusedIndex ?? 0,
        sizes: state.sizes,
    } as { panes: unknown[]; focusedIndex: number });
}

/**
 * Patch peer fields on any pane that matches destination_hash (pure list transform).
 */
export function applyPatchToPanePeers(panes: Pane[], destinationHash: string, patch: Partial<Peer>): Pane[] {
    return (panes || []).map((pane) => {
        if (pane.peer && pane.peer.destination_hash === destinationHash) {
            return { ...pane, peer: { ...pane.peer, ...patch } };
        }
        return pane;
    });
}
