// @ts-check

import { computed, ref, watch } from "vue";

import NotificationUtils from "../NotificationUtils";
import Utils from "../Utils";
import { setOpenDestinationHashes } from "../activeConversationStore.js";
import { loadMessagePanes, saveMessagePanes } from "../browserLayoutStore";

/**
 * Multi-pane conversation layout state for MessagesPage: the pane list,
 * focused pane and selectedPeer proxy, flex sizing with pointer resizing,
 * drag/drop between panes and the add-zone, viewport media queries, and
 * localStorage persistence of the whole layout.
 *
 * options.isPopoutMode and options.getConfig read host state that stays on
 * the page (route-driven popout flag, config object). options.onPeerClick,
 * options.peerFromDestinationHash, options.getPaneViewers,
 * options.onCloseConversationViewer and options.syncRouteToFocusedPane are
 * host callbacks for peer selection, the viewer registry, and route sync.
 *
 * @param {object} [options]
 * @param {() => boolean} [options.isPopoutMode]
 * @param {() => any} [options.getConfig]
 * @param {(destinationHash: string) => any} [options.peerFromDestinationHash]
 * @param {(peer: any) => void} [options.onPeerClick]
 * @param {() => any} [options.getPaneViewers]
 * @param {() => void} [options.onCloseConversationViewer]
 * @param {() => void} [options.syncRouteToFocusedPane]
 */
export function useMessagePanes(options = {}) {
    const {
        isPopoutMode = () => false,
        getConfig = () => null,
        peerFromDestinationHash = () => null,
        onPeerClick = () => {},
        getPaneViewers = () => null,
        onCloseConversationViewer = () => {},
        syncRouteToFocusedPane = () => {},
    } = options;

    /** @type {import("vue").Ref<Array<{ id: number, peer: any }>>} */
    const panes = ref([{ id: 1, peer: null }]);
    const focusedPaneId = ref(1);
    const nextPaneId = ref(2);
    /** @type {import("vue").Ref<Record<number, number>>} */
    const paneFlex = ref({});
    /** @type {import("vue").Ref<string | null>} */
    const resizingPaneIds = ref(null);
    /** @type {import("vue").Ref<number | null>} */
    const dragOverPaneId = ref(null);
    const isDragOverAddZone = ref(false);
    const isConversationDragging = ref(false);
    const isWideViewport = ref(false);
    const isWideEnoughForThreePanes = ref(false);
    /** @type {import("vue").Ref<MediaQueryList | null>} */
    const paneViewportQuery = ref(null);
    /** @type {import("vue").Ref<((event: any) => void) | null>} */
    const paneViewportListener = ref(null);
    /** @type {import("vue").Ref<MediaQueryList | null>} */
    const threePaneViewportQuery = ref(null);
    /** @type {import("vue").Ref<((event: any) => void) | null>} */
    const threePaneViewportListener = ref(null);

    /** @type {any} */
    let resizeContext = null;
    /** @type {EventListener | null} */
    let boundPaneResizeMove = null;
    /** @type {EventListener | null} */
    let boundPaneResizeEnd = null;

    const focusedPane = computed(() => {
        return panes.value.find((pane) => pane.id === focusedPaneId.value) || panes.value[0] || null;
    });

    const selectedPeer = computed({
        get() {
            return focusedPane.value?.peer ?? null;
        },
        set(peer) {
            const pane = focusedPane.value;
            if (pane) {
                pane.peer = peer;
            }
        },
    });

    const multiPaneEnabled = computed(() => {
        return getConfig()?.messages_multi_pane_enabled !== false;
    });

    const maxPanes = computed(() => {
        if (isPopoutMode() || !isWideViewport.value || !multiPaneEnabled.value) {
            return 1;
        }
        return isWideEnoughForThreePanes.value ? 3 : 2;
    });

    const visiblePanes = computed(() => {
        let list;
        if (maxPanes.value <= 1) {
            list = focusedPane.value ? [focusedPane.value] : panes.value.slice(0, 1);
        } else {
            list = panes.value.slice(0, maxPanes.value);
        }
        if (list.length <= 1) {
            return list;
        }
        const hasEmptyPane = list.some((pane) => !pane.peer);
        if (!hasEmptyPane) {
            return list;
        }
        return list.filter((pane) => pane.peer || pane.id === focusedPaneId.value);
    });

    const multiPaneActive = computed(() => {
        return visiblePanes.value.length > 1;
    });

    const canAddPane = computed(() => {
        return (
            !isPopoutMode() && isWideViewport.value && panes.value.length < maxPanes.value && selectedPeer.value != null
        );
    });

    const paneLayoutSignature = computed(() => {
        const hashes = panes.value.map((pane) => pane.peer?.destination_hash || "").join("\u241f");
        const focusedIndex = panes.value.findIndex((pane) => pane.id === focusedPaneId.value);
        return `${focusedIndex}\u241e${hashes}`;
    });

    watch(paneLayoutSignature, () => {
        persistPanes();
        syncOpenDestinationHashes();
    });

    function slimPeer(peer) {
        if (!peer || !peer.destination_hash) {
            return null;
        }
        return {
            destination_hash: peer.destination_hash,
            display_name: peer.display_name ?? null,
            custom_display_name: peer.custom_display_name ?? null,
        };
    }

    function restorePanes(routeHash) {
        const saved = loadMessagePanes();
        if (!saved || saved.panes.length === 0) {
            return;
        }

        panes.value = saved.panes.map((peer) => ({
            id: nextPaneId.value++,
            peer: peer && peer.destination_hash ? { ...peer } : null,
        }));

        panes.value.forEach((pane, index) => {
            const size = Array.isArray(saved.sizes) ? saved.sizes[index] : null;
            paneFlex.value[pane.id] = typeof size === "number" && size > 0 ? size : 1;
        });

        const focusedIndex =
            Number.isInteger(saved.focusedIndex) && saved.focusedIndex >= 0 && saved.focusedIndex < panes.value.length
                ? saved.focusedIndex
                : 0;
        focusedPaneId.value = panes.value[focusedIndex].id;

        if (routeHash) {
            const match = panes.value.find((pane) => pane.peer?.destination_hash === routeHash);
            if (match) {
                focusedPaneId.value = match.id;
            }
        }
    }

    function persistPanes() {
        const focusedIndex = panes.value.findIndex((pane) => pane.id === focusedPaneId.value);
        saveMessagePanes({
            panes: panes.value.map((pane) => slimPeer(pane.peer)),
            sizes: panes.value.map((pane) => paneFlexValue(pane.id)),
            focusedIndex: focusedIndex < 0 ? 0 : focusedIndex,
        });
    }

    function syncOpenDestinationHashes() {
        const hashes = panes.value
            .map((pane) => pane.peer?.destination_hash)
            .filter((h) => typeof h === "string" && h.length > 0);
        setOpenDestinationHashes(hashes);
        NotificationUtils.syncAndroidNotificationContext(hashes, Boolean(getConfig()?.do_not_disturb_enabled));
    }

    function applyToPanePeers(destinationHash, patch) {
        for (const pane of panes.value) {
            if (pane.peer && pane.peer.destination_hash === destinationHash) {
                pane.peer = { ...pane.peer, ...patch };
            }
        }
    }

    function focusPane(paneId) {
        if (panes.value.some((pane) => pane.id === paneId)) {
            focusedPaneId.value = paneId;
        }
    }

    function addPane() {
        const existingEmpty = panes.value.find((pane) => !pane.peer);
        if (existingEmpty) {
            focusedPaneId.value = existingEmpty.id;
            return;
        }
        if (!canAddPane.value) {
            return;
        }
        const id = nextPaneId.value++;
        panes.value.push({ id, peer: null });
        focusedPaneId.value = id;
    }

    function paneFlexValue(paneId) {
        if (visiblePanes.value.length <= 1) {
            return 1;
        }
        const pane = visiblePanes.value.find((entry) => entry.id === paneId);
        if (!pane?.peer) {
            return 1;
        }
        const value = paneFlex.value[paneId];
        return typeof value === "number" && value > 0 ? value : 1;
    }

    function startPaneResize(event, leftPaneId, rightPaneId) {
        if (!isWideViewport.value || (event.button != null && event.button !== 0)) {
            return;
        }
        const resizer = event.currentTarget;
        const leftEl = resizer?.previousElementSibling;
        const rightEl = resizer?.nextElementSibling;
        if (!leftEl || !rightEl) {
            return;
        }
        event.preventDefault();

        const leftWidth = leftEl.getBoundingClientRect().width;
        const rightWidth = rightEl.getBoundingClientRect().width;
        const combinedWidth = leftWidth + rightWidth;
        if (combinedWidth <= 0) {
            return;
        }

        const combinedFlex = paneFlexValue(leftPaneId) + paneFlexValue(rightPaneId);

        resizeContext = {
            leftPaneId,
            rightPaneId,
            startX: event.clientX,
            leftWidth,
            combinedWidth,
            combinedFlex,
            minWidth: Math.min(220, combinedWidth / 2),
        };
        resizingPaneIds.value = `${leftPaneId}:${rightPaneId}`;

        boundPaneResizeMove = onPaneResizeMove;
        boundPaneResizeEnd = endPaneResize;
        window.addEventListener("pointermove", boundPaneResizeMove);
        window.addEventListener("pointerup", boundPaneResizeEnd);
        document.body.style.userSelect = "none";
        document.body.style.cursor = "col-resize";
    }

    function onPaneResizeMove(event) {
        const ctx = resizeContext;
        if (!ctx) {
            return;
        }
        const delta = event.clientX - ctx.startX;
        let newLeftWidth = ctx.leftWidth + delta;
        const maxLeftWidth = ctx.combinedWidth - ctx.minWidth;
        if (newLeftWidth < ctx.minWidth) {
            newLeftWidth = ctx.minWidth;
        } else if (newLeftWidth > maxLeftWidth) {
            newLeftWidth = maxLeftWidth;
        }

        const leftFlex = ctx.combinedFlex * (newLeftWidth / ctx.combinedWidth);
        paneFlex.value[ctx.leftPaneId] = leftFlex;
        paneFlex.value[ctx.rightPaneId] = ctx.combinedFlex - leftFlex;
    }

    function endPaneResize() {
        window.removeEventListener("pointermove", boundPaneResizeMove);
        window.removeEventListener("pointerup", boundPaneResizeEnd);
        boundPaneResizeMove = null;
        boundPaneResizeEnd = null;
        resizeContext = null;
        resizingPaneIds.value = null;
        document.body.style.userSelect = "";
        document.body.style.cursor = "";
        persistPanes();
    }

    function resetPaneSizes() {
        for (const pane of panes.value) {
            paneFlex.value[pane.id] = 1;
        }
        persistPanes();
    }

    function teardownPaneResize() {
        if (boundPaneResizeMove) {
            window.removeEventListener("pointermove", boundPaneResizeMove);
        }
        if (boundPaneResizeEnd) {
            window.removeEventListener("pointerup", boundPaneResizeEnd);
        }
        boundPaneResizeMove = null;
        boundPaneResizeEnd = null;
        resizeContext = null;
    }

    function openConversationInPane(paneId, destinationHash) {
        const normalized = Utils.normalizeMeshchatHashHex(destinationHash || "");
        if (normalized.length !== 32) {
            return;
        }
        const pane = panes.value.find((entry) => entry.id === paneId);
        if (!pane) {
            return;
        }
        focusedPaneId.value = paneId;
        const peer = peerFromDestinationHash(normalized);
        onPeerClick(peer);
        const viewer = getPaneViewers()?.[paneId];
        viewer?.markConversationAsRead?.(peer);
    }

    function onPaneDragOver(paneId) {
        if (!isWideViewport.value) {
            return;
        }
        dragOverPaneId.value = paneId;
    }

    function onPaneDragLeave(paneId) {
        if (dragOverPaneId.value === paneId) {
            dragOverPaneId.value = null;
        }
    }

    function onPaneDrop(paneId, event) {
        dragOverPaneId.value = null;
        const hash = event?.dataTransfer?.getData("text/plain");
        if (hash) {
            openConversationInPane(paneId, hash);
        }
    }

    function onAddZoneDragOver() {
        if (canAddPane.value) {
            isDragOverAddZone.value = true;
        }
    }

    function onAddZoneDragLeave() {
        isDragOverAddZone.value = false;
    }

    function onAddZoneDrop(event) {
        isDragOverAddZone.value = false;
        const hash = event?.dataTransfer?.getData("text/plain");
        if (!hash || panes.value.length >= maxPanes.value) {
            return;
        }
        const id = nextPaneId.value++;
        panes.value.push({ id, peer: null });
        openConversationInPane(id, hash);
    }

    function openPeerInSplit(hash) {
        if (!hash || panes.value.length >= maxPanes.value || !isWideViewport.value) {
            return;
        }
        const id = nextPaneId.value++;
        panes.value.push({ id, peer: null });
        openConversationInPane(id, hash);
    }

    function onConversationDragStart() {
        isConversationDragging.value = true;
        // dragend normally ends the drag on the source row, but if that row
        // unmounts mid-drag (list re-sort, sidebar teardown) the event can
        // be lost; window-level drop/dragend settle the state regardless.
        window.addEventListener("dragend", onWindowDragSettled);
        window.addEventListener("drop", onWindowDragSettled);
    }

    function onConversationDragEnd() {
        isConversationDragging.value = false;
        teardownConversationDragWatch();
    }

    function onWindowDragSettled() {
        isConversationDragging.value = false;
        teardownConversationDragWatch();
    }

    function teardownConversationDragWatch() {
        window.removeEventListener("dragend", onWindowDragSettled);
        window.removeEventListener("drop", onWindowDragSettled);
    }

    function onPanePeerUpdate(paneId, peer) {
        focusPane(paneId);
        onPeerClick(peer);
    }

    function onPaneClose(paneId) {
        const index = panes.value.findIndex((pane) => pane.id === paneId);
        if (index === -1) {
            return;
        }

        if (panes.value.length > 1) {
            panes.value.splice(index, 1);
            delete paneFlex.value[paneId];
            const viewers = getPaneViewers();
            if (viewers) {
                delete viewers[paneId];
            }
            if (panes.value.length === 1) {
                paneFlex.value[panes.value[0].id] = 1;
            }
            if (focusedPaneId.value === paneId) {
                const neighbour = panes.value[index] || panes.value[index - 1] || panes.value[0];
                focusedPaneId.value = neighbour.id;
            }
            syncRouteToFocusedPane();
            return;
        }

        onCloseConversationViewer();
    }

    function setupPaneViewportWatchers() {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            isWideViewport.value = false;
            isWideEnoughForThreePanes.value = false;
            return;
        }

        paneViewportQuery.value = window.matchMedia("(min-width: 768px)");
        isWideViewport.value = paneViewportQuery.value.matches;
        paneViewportListener.value = (event) => {
            isWideViewport.value = event.matches;
        };
        addMediaListener(paneViewportQuery.value, paneViewportListener.value);

        threePaneViewportQuery.value = window.matchMedia("(min-width: 1280px)");
        isWideEnoughForThreePanes.value = threePaneViewportQuery.value.matches;
        threePaneViewportListener.value = (event) => {
            isWideEnoughForThreePanes.value = event.matches;
        };
        addMediaListener(threePaneViewportQuery.value, threePaneViewportListener.value);
    }

    function teardownPaneViewportWatchers() {
        removeMediaListener(paneViewportQuery.value, paneViewportListener.value);
        removeMediaListener(threePaneViewportQuery.value, threePaneViewportListener.value);
        paneViewportQuery.value = null;
        paneViewportListener.value = null;
        threePaneViewportQuery.value = null;
        threePaneViewportListener.value = null;
    }

    function addMediaListener(query, listener) {
        if (!query || !listener) {
            return;
        }
        if (typeof query.addEventListener === "function") {
            query.addEventListener("change", listener);
        } else if (typeof query.addListener === "function") {
            query.addListener(listener);
        }
    }

    function removeMediaListener(query, listener) {
        if (!query || !listener) {
            return;
        }
        if (typeof query.removeEventListener === "function") {
            query.removeEventListener("change", listener);
        } else if (typeof query.removeListener === "function") {
            query.removeListener(listener);
        }
    }

    return {
        panes,
        focusedPaneId,
        nextPaneId,
        paneFlex,
        resizingPaneIds,
        dragOverPaneId,
        isDragOverAddZone,
        isConversationDragging,
        isWideViewport,
        isWideEnoughForThreePanes,
        paneViewportQuery,
        paneViewportListener,
        threePaneViewportQuery,
        threePaneViewportListener,
        focusedPane,
        selectedPeer,
        multiPaneEnabled,
        maxPanes,
        visiblePanes,
        multiPaneActive,
        canAddPane,
        paneLayoutSignature,
        slimPeer,
        restorePanes,
        persistPanes,
        syncOpenDestinationHashes,
        applyToPanePeers,
        focusPane,
        addPane,
        paneFlexValue,
        startPaneResize,
        onPaneResizeMove,
        endPaneResize,
        resetPaneSizes,
        teardownPaneResize,
        openConversationInPane,
        onPaneDragOver,
        onPaneDragLeave,
        onPaneDrop,
        onAddZoneDragOver,
        onAddZoneDragLeave,
        onAddZoneDrop,
        openPeerInSplit,
        onConversationDragStart,
        onConversationDragEnd,
        onWindowDragSettled,
        teardownConversationDragWatch,
        onPanePeerUpdate,
        onPaneClose,
        setupPaneViewportWatchers,
        teardownPaneViewportWatchers,
        addMediaListener,
        removeMediaListener,
    };
}
