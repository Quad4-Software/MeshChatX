// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    applyPatchToPanePeers,
    buildPersistedPaneState,
    maxPanesFromWidth,
    paneFlexValue,
    restorePanesFromSaved,
    selectVisiblePanes,
} from "@/features/messages/lib/paneLayout.ts";

const peer = (hash) => ({ destination_hash: hash, display_name: hash });

describe("MessagesPage multi-pane layout", () => {
    it("limits panes by viewport, popout, and configuration", () => {
        expect(maxPanesFromWidth()).toBe(1);
        expect(maxPanesFromWidth({ isWideViewport: true })).toBe(2);
        expect(maxPanesFromWidth({ isWideViewport: true, isWideEnoughForThreePanes: true })).toBe(3);
        expect(maxPanesFromWidth({ isWideViewport: true, isPopoutMode: true })).toBe(1);
        expect(maxPanesFromWidth({ isWideViewport: true, multiPaneEnabled: false })).toBe(1);
    });

    it("shows only the focused pane on narrow viewports", () => {
        const panes = [
            { id: 1, peer: peer("a".repeat(32)) },
            { id: 2, peer: peer("b".repeat(32)) },
        ];

        expect(selectVisiblePanes({ panes, focusedPaneId: 2, maxPanes: 1 })).toEqual([panes[1]]);
    });

    it("hides an unfocused empty pane while preserving a focused selector pane", () => {
        const panes = [
            { id: 1, peer: peer("a".repeat(32)) },
            { id: 2, peer: null },
        ];

        expect(selectVisiblePanes({ panes, focusedPaneId: 1, maxPanes: 2 })).toEqual([panes[0]]);
        expect(selectVisiblePanes({ panes, focusedPaneId: 2, maxPanes: 2 })).toEqual(panes);
    });

    it("uses equal flex for a single pane and saved flex for populated splits", () => {
        const panes = [
            { id: 1, peer: peer("a".repeat(32)) },
            { id: 2, peer: peer("b".repeat(32)) },
        ];

        expect(paneFlexValue(1, { 1: 2.5 }, [panes[0]])).toBe(1);
        expect(paneFlexValue(1, { 1: 2.5 }, panes)).toBe(2.5);
        expect(paneFlexValue(2, {}, panes)).toBe(1);
    });

    it("persists peer slices, flex values, and focused index", () => {
        const panes = [
            { id: 3, peer: peer("a".repeat(32)) },
            { id: 4, peer: peer("b".repeat(32)) },
        ];

        expect(
            buildPersistedPaneState({
                panes,
                focusedPaneId: 4,
                paneFlex: { 3: 1.2, 4: 0.8 },
                visiblePanes: panes,
            })
        ).toEqual({
            panes: [
                {
                    destination_hash: "a".repeat(32),
                    display_name: "a".repeat(32),
                    custom_display_name: null,
                },
                {
                    destination_hash: "b".repeat(32),
                    display_name: "b".repeat(32),
                    custom_display_name: null,
                },
            ],
            sizes: [1.2, 0.8],
            focusedIndex: 1,
        });
    });

    it("restores panes and lets a route hash choose focus", () => {
        const routeHash = "b".repeat(32);
        const restored = restorePanesFromSaved(
            {
                panes: [peer("a".repeat(32)), peer(routeHash)],
                sizes: [1.25, 0.75],
                focusedIndex: 0,
            },
            routeHash,
            5
        );

        expect(restored).toMatchObject({
            focusedPaneId: 6,
            nextPaneId: 7,
            paneFlex: { 5: 1.25, 6: 0.75 },
        });
        expect(restored.panes.map((pane) => pane.id)).toEqual([5, 6]);
    });

    it("patches every pane that displays the same destination", () => {
        const hash = "c".repeat(32);
        const panes = [
            { id: 1, peer: { ...peer(hash), is_tracking: false } },
            { id: 2, peer: { ...peer(hash), is_tracking: false } },
        ];

        const updated = applyPatchToPanePeers(panes, hash, { is_tracking: true });
        expect(updated.every((pane) => pane.peer.is_tracking)).toBe(true);
        expect(panes.every((pane) => pane.peer.is_tracking === false)).toBe(true);
    });
});
