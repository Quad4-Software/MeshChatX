// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { nextTick } from "vue";
import { useMessagePanes } from "../../meshchatx/src/frontend/js/messages/useMessagePanes.js";

const hash = (c) => c.repeat(32);

describe("useMessagePanes", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    afterEach(() => {
        document.body.style.userSelect = "";
        document.body.style.cursor = "";
    });

    it("starts with a single focused empty pane", () => {
        const m = useMessagePanes();
        expect(m.panes.value).toHaveLength(1);
        expect(m.focusedPaneId.value).toBe(m.panes.value[0].id);
        expect(m.focusedPane.value).toEqual({ id: 1, peer: null });
        expect(m.selectedPeer.value).toBeNull();
        expect(m.multiPaneActive.value).toBe(false);
    });

    it("selectedPeer get/set is backed by the focused pane", () => {
        const m = useMessagePanes();
        m.selectedPeer.value = { destination_hash: hash("a") };
        expect(m.focusedPane.value.peer).toMatchObject({ destination_hash: hash("a") });
        expect(m.selectedPeer.value).toMatchObject({ destination_hash: hash("a") });
    });

    it("limits panes by viewport width, popout mode, and config", () => {
        const m = useMessagePanes();
        expect(m.maxPanes.value).toBe(1);

        m.isWideViewport.value = true;
        expect(m.maxPanes.value).toBe(2);

        m.isWideEnoughForThreePanes.value = true;
        expect(m.maxPanes.value).toBe(3);

        const popout = useMessagePanes({ isPopoutMode: () => true });
        popout.isWideViewport.value = true;
        popout.isWideEnoughForThreePanes.value = true;
        expect(popout.maxPanes.value).toBe(1);

        const disabled = useMessagePanes({ getConfig: () => ({ messages_multi_pane_enabled: false }) });
        disabled.isWideViewport.value = true;
        disabled.isWideEnoughForThreePanes.value = true;
        expect(disabled.multiPaneEnabled.value).toBe(false);
        expect(disabled.maxPanes.value).toBe(1);
    });

    it("addPane adds and focuses a new empty pane when allowed", () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };
        expect(m.canAddPane.value).toBe(true);

        m.addPane();
        expect(m.panes.value).toHaveLength(2);
        expect(m.focusedPaneId.value).toBe(m.panes.value[1].id);
        expect(m.panes.value[1].peer).toBeNull();
        expect(m.multiPaneActive.value).toBe(true);
    });

    it("does not add panes beyond maxPanes and reuses an empty pane", () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        m.isWideEnoughForThreePanes.value = false;
        m.selectedPeer.value = { destination_hash: hash("a") };

        m.addPane();
        m.panes.value[1].peer = { destination_hash: hash("b") };
        m.addPane();
        expect(m.panes.value).toHaveLength(2);

        m.panes.value[1].peer = null;
        const emptyId = m.panes.value[1].id;
        m.focusedPaneId.value = m.panes.value[0].id;
        m.addPane();
        expect(m.panes.value).toHaveLength(2);
        expect(m.focusedPaneId.value).toBe(emptyId);
    });

    it("canAddPane requires a selected peer and wide viewport", () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        expect(m.canAddPane.value).toBe(false);
        m.selectedPeer.value = { destination_hash: hash("a") };
        expect(m.canAddPane.value).toBe(true);
        m.isWideViewport.value = false;
        expect(m.canAddPane.value).toBe(false);
    });

    it("hides unfocused empty panes but keeps the focused one visible", () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };
        m.addPane();

        // focused empty pane stays visible for conversation selection
        expect(m.visiblePanes.value).toHaveLength(2);

        // unfocused empty pane is hidden so the active chat fills the width
        m.focusedPaneId.value = m.panes.value[0].id;
        expect(m.visiblePanes.value).toHaveLength(1);
        expect(m.visiblePanes.value[0].id).toBe(m.panes.value[0].id);
    });

    it("focusPane ignores unknown pane ids", () => {
        const m = useMessagePanes();
        const before = m.focusedPaneId.value;
        m.focusPane(999);
        expect(m.focusedPaneId.value).toBe(before);
        m.focusPane(m.panes.value[0].id);
        expect(m.focusedPaneId.value).toBe(m.panes.value[0].id);
    });

    it("persists pane layout when the signature changes", async () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a"), display_name: "Peer A" };
        await nextTick();
        m.addPane();
        m.panes.value[1].peer = { destination_hash: hash("b"), display_name: "Peer B" };
        await nextTick();

        const saved = JSON.parse(localStorage.getItem("meshchatx.messages.panes"));
        expect(saved.panes).toHaveLength(2);
        expect(saved.panes[0]).toMatchObject({ destination_hash: hash("a"), display_name: "Peer A" });
        expect(saved.panes[1]).toMatchObject({ destination_hash: hash("b") });
        expect(saved.focusedIndex).toBe(1);
    });

    it("restores persisted panes with focused index, sizes, and route hash", () => {
        localStorage.setItem(
            "meshchatx.messages.panes",
            JSON.stringify({
                panes: [
                    { destination_hash: hash("a"), display_name: "Peer A", custom_display_name: null },
                    { destination_hash: hash("b"), display_name: "Peer B", custom_display_name: null },
                ],
                sizes: [0.4, 1.6],
                focusedIndex: 1,
            })
        );

        const m = useMessagePanes();
        m.restorePanes(null);
        expect(m.panes.value).toHaveLength(2);
        expect(m.panes.value[0].peer).toMatchObject({ destination_hash: hash("a") });
        expect(m.focusedPaneId.value).toBe(m.panes.value[1].id);
        m.isWideViewport.value = true;
        expect(m.paneFlex.value[m.panes.value[0].id]).toBe(0.4);
        expect(m.paneFlex.value[m.panes.value[1].id]).toBe(1.6);

        const routed = useMessagePanes();
        routed.restorePanes(hash("a"));
        expect(routed.focusedPaneId.value).toBe(routed.panes.value[0].id);
    });

    it("paneFlexValue defaults to 1 and reflects custom sizes when multiple panes are visible", () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };
        m.addPane();
        m.panes.value[1].peer = { destination_hash: hash("b") };

        const leftId = m.panes.value[0].id;
        const rightId = m.panes.value[1].id;
        expect(m.paneFlexValue(leftId)).toBe(1);
        m.paneFlex.value[leftId] = 2.5;
        expect(m.paneFlexValue(leftId)).toBe(2.5);
        expect(m.paneFlexValue(rightId)).toBe(1);
    });

    it("resizes adjacent panes and keeps combined flex constant", () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };
        m.addPane();
        m.panes.value[1].peer = { destination_hash: hash("b") };

        const leftId = m.panes.value[0].id;
        const rightId = m.panes.value[1].id;
        const fakeEvent = {
            button: 0,
            clientX: 0,
            preventDefault: () => {},
            currentTarget: {
                previousElementSibling: { getBoundingClientRect: () => ({ width: 300 }) },
                nextElementSibling: { getBoundingClientRect: () => ({ width: 300 }) },
            },
        };

        m.startPaneResize(fakeEvent, leftId, rightId);
        expect(m.resizingPaneIds.value).toBe(`${leftId}:${rightId}`);
        m.onPaneResizeMove({ clientX: 60 });

        expect(m.paneFlexValue(leftId)).toBeCloseTo(1.2, 5);
        expect(m.paneFlexValue(rightId)).toBeCloseTo(0.8, 5);

        m.endPaneResize();
        expect(m.resizingPaneIds.value).toBeNull();

        const saved = JSON.parse(localStorage.getItem("meshchatx.messages.panes"));
        expect(saved.sizes[0]).toBeCloseTo(1.2, 5);
        expect(saved.sizes[1]).toBeCloseTo(0.8, 5);
    });

    it("ignores resize start on narrow viewports and non-left buttons", () => {
        const m = useMessagePanes();
        const fakeEvent = {
            button: 0,
            clientX: 0,
            preventDefault: vi.fn(),
            currentTarget: {
                previousElementSibling: { getBoundingClientRect: () => ({ width: 300 }) },
                nextElementSibling: { getBoundingClientRect: () => ({ width: 300 }) },
            },
        };
        m.startPaneResize(fakeEvent, 1, 2);
        expect(m.resizingPaneIds.value).toBeNull();

        m.isWideViewport.value = true;
        m.startPaneResize({ ...fakeEvent, button: 2 }, 1, 2);
        expect(m.resizingPaneIds.value).toBeNull();
    });

    it("resetPaneSizes restores equal flex and persists", async () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };
        m.addPane();
        m.paneFlex.value[m.panes.value[0].id] = 3;

        m.resetPaneSizes();
        for (const pane of m.panes.value) {
            expect(m.paneFlexValue(pane.id)).toBe(1);
        }
        await nextTick();
        const saved = JSON.parse(localStorage.getItem("meshchatx.messages.panes"));
        expect(saved.sizes).toEqual([1, 1]);
    });

    it("onPaneClose removes a pane and focuses a neighbour", () => {
        const syncRouteToFocusedPane = vi.fn();
        const m = useMessagePanes({ syncRouteToFocusedPane });
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };
        m.addPane();
        const firstId = m.panes.value[0].id;
        const secondId = m.panes.value[1].id;

        m.onPaneClose(secondId);
        expect(m.panes.value).toHaveLength(1);
        expect(m.focusedPaneId.value).toBe(firstId);
        expect(syncRouteToFocusedPane).toHaveBeenCalled();
    });

    it("onPaneClose on the last pane delegates to onCloseConversationViewer", () => {
        const onCloseConversationViewer = vi.fn();
        const m = useMessagePanes({ onCloseConversationViewer });
        m.onPaneClose(m.panes.value[0].id);
        expect(m.panes.value).toHaveLength(1);
        expect(onCloseConversationViewer).toHaveBeenCalledTimes(1);
    });

    it("onPanePeerUpdate focuses the pane and forwards the peer to onPeerClick", () => {
        const onPeerClick = vi.fn();
        const m = useMessagePanes({ onPeerClick });
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };
        m.addPane();
        const secondId = m.panes.value[1].id;
        m.focusedPaneId.value = m.panes.value[0].id;

        const peer = { destination_hash: hash("b") };
        m.onPanePeerUpdate(secondId, peer);
        expect(m.focusedPaneId.value).toBe(secondId);
        expect(onPeerClick).toHaveBeenCalledWith(peer);
    });

    it("onPaneDrop opens the dropped hash in the target pane", () => {
        const onPeerClick = vi.fn((peer) => {
            m.selectedPeer.value = peer;
        });
        const markConversationAsRead = vi.fn();
        const peer = { destination_hash: hash("8"), display_name: "Dropped" };
        const m = useMessagePanes({
            onPeerClick,
            peerFromDestinationHash: () => peer,
            getPaneViewers: () => ({ 1: { markConversationAsRead } }),
        });
        m.isWideViewport.value = true;

        m.onPaneDrop(1, { dataTransfer: { getData: () => hash("8") } });
        expect(onPeerClick).toHaveBeenCalledWith(peer);
        expect(m.panes.value[0].peer).toMatchObject({ destination_hash: hash("8") });
        expect(markConversationAsRead).toHaveBeenCalledWith(peer);
        expect(m.dragOverPaneId.value).toBeNull();
    });

    it("onPaneDrop ignores invalid hashes", () => {
        const onPeerClick = vi.fn();
        const m = useMessagePanes({ onPeerClick });
        m.onPaneDrop(1, { dataTransfer: { getData: () => "short" } });
        expect(onPeerClick).not.toHaveBeenCalled();
    });

    it("drag over/leave tracks the hovered pane only on wide viewports", () => {
        const m = useMessagePanes();
        m.onPaneDragOver(1);
        expect(m.dragOverPaneId.value).toBeNull();

        m.isWideViewport.value = true;
        m.onPaneDragOver(1);
        expect(m.dragOverPaneId.value).toBe(1);
        m.onPaneDragLeave(2);
        expect(m.dragOverPaneId.value).toBe(1);
        m.onPaneDragLeave(1);
        expect(m.dragOverPaneId.value).toBeNull();
    });

    it("add-zone drop creates a split pane for the dropped hash", () => {
        const onPeerClick = vi.fn((peer) => {
            m.selectedPeer.value = peer;
        });
        const m = useMessagePanes({
            onPeerClick,
            peerFromDestinationHash: (h) => ({ destination_hash: h }),
        });
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };

        m.onAddZoneDragOver();
        expect(m.isDragOverAddZone.value).toBe(true);
        m.onAddZoneDrop({ dataTransfer: { getData: () => hash("6") } });
        expect(m.isDragOverAddZone.value).toBe(false);
        expect(m.panes.value).toHaveLength(2);
        expect(m.panes.value[1].peer).toMatchObject({ destination_hash: hash("6") });
    });

    it("openPeerInSplit adds a pane and opens the peer in it", () => {
        const onPeerClick = vi.fn((peer) => {
            m.selectedPeer.value = peer;
        });
        const m = useMessagePanes({
            onPeerClick,
            peerFromDestinationHash: (h) => ({ destination_hash: h }),
        });
        m.isWideViewport.value = true;
        m.selectedPeer.value = { destination_hash: hash("a") };

        m.openPeerInSplit(hash("c"));
        expect(m.panes.value).toHaveLength(2);
        expect(m.panes.value[1].peer).toMatchObject({ destination_hash: hash("c") });
        expect(m.focusedPaneId.value).toBe(m.panes.value[1].id);
    });

    it("openPeerInSplit is a no-op without a hash or on narrow viewports", () => {
        const onPeerClick = vi.fn();
        const m = useMessagePanes({ onPeerClick });
        m.openPeerInSplit(null);
        m.openPeerInSplit(hash("c"));
        expect(m.panes.value).toHaveLength(1);
        expect(onPeerClick).not.toHaveBeenCalled();
    });

    it("conversation drag state settles on dragend, drop, or source dragend", () => {
        const m = useMessagePanes();
        m.onConversationDragStart();
        expect(m.isConversationDragging.value).toBe(true);
        window.dispatchEvent(new Event("drop"));
        expect(m.isConversationDragging.value).toBe(false);

        m.onConversationDragStart();
        window.dispatchEvent(new Event("dragend"));
        expect(m.isConversationDragging.value).toBe(false);

        m.onConversationDragStart();
        m.onConversationDragEnd();
        expect(m.isConversationDragging.value).toBe(false);
    });

    it("applyToPanePeers patches every pane showing a destination", () => {
        const m = useMessagePanes();
        const dest = hash("3");
        m.selectedPeer.value = { destination_hash: dest, is_tracking: false };
        m.panes.value.push({ id: 99, peer: { destination_hash: dest, is_tracking: false } });
        m.panes.value.push({ id: 100, peer: { destination_hash: hash("4"), is_tracking: false } });

        m.applyToPanePeers(dest, { is_tracking: true });
        expect(m.panes.value[0].peer.is_tracking).toBe(true);
        expect(m.panes.value[1].peer.is_tracking).toBe(true);
        expect(m.panes.value[2].peer.is_tracking).toBe(false);
    });

    it("slimPeer keeps only persisted fields", () => {
        const m = useMessagePanes();
        expect(m.slimPeer(null)).toBeNull();
        expect(m.slimPeer({ display_name: "x" })).toBeNull();
        expect(
            m.slimPeer({ destination_hash: hash("a"), display_name: "A", custom_display_name: "C", extra: 1 })
        ).toEqual({ destination_hash: hash("a"), display_name: "A", custom_display_name: "C" });
    });

    it("viewport watchers set flags false without matchMedia and clear queries on teardown", () => {
        const m = useMessagePanes();
        m.isWideViewport.value = true;
        m.isWideEnoughForThreePanes.value = true;
        m.setupPaneViewportWatchers();
        expect(m.isWideViewport.value).toBe(false);
        expect(m.isWideEnoughForThreePanes.value).toBe(false);
        m.teardownPaneViewportWatchers();
        expect(m.paneViewportQuery.value).toBeNull();
        expect(m.threePaneViewportQuery.value).toBeNull();
    });
});
