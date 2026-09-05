<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import WebSocketConnection from "../../js/WebSocketConnection.js";
    import Utils from "../../js/Utils.js";
    import GlobalState, { mergeGlobalConfig } from "../../js/GlobalState.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import DialogUtils from "../../js/DialogUtils.js";
    import DownloadUtils from "../../js/DownloadUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import NotificationUtils from "../../js/NotificationUtils.js";
    import { setOpenDestinationHashes } from "../../js/activeConversationStore.js";
    import {
        conversationListSignature,
        countUnreadConversations,
        syncConversationListInPlace,
    } from "../../js/lxmfConversationListSync.js";
    import { loadFeatureSidebarCollapsed, saveFeatureSidebarCollapsed } from "../../js/browserLayoutStore.js";
    import { isRetryableHttpError } from "../../js/httpRetry.js";
    import { runWhenIdentityHttpReady } from "../../js/identityHttpReady.js";
    import { t } from "../../js/i18n.js";
    import {
        applyOutboundComposeEnqueued,
        applyOutboundMessageCreated,
        applyOutboundMessageStateUpdated,
    } from "./lib/conversationListApply.js";
    import { buildConversationQueryParams } from "./lib/conversationQuery.js";
    import {
        loadAndRestorePanes,
        maxPanesFromWidth,
        paneLayoutSignature as buildPaneLayoutSignature,
        persistPanesState,
        selectVisiblePanes,
        applyPatchToPanePeers,
    } from "./lib/paneLayout.js";
    import {
        updatePeerFromAnnounce,
        updatePeerFromConversation,
        shouldUpdatePanePeerDisplayName,
        ANONYMOUS_PEER_DISPLAY_NAME,
    } from "./lib/peerAnnounce.js";
    import {
        applyOptimisticUnreadClear,
        destinationsNeedingUnreadDismiss,
        findUnreadTarget,
        revertOptimisticUnreadClear,
        nextUnreadConversationsCount,
    } from "./lib/unreadDismiss.js";
    import type { Conversation, Folder, MessagesConfig, Pane, Peer } from "./lib/types.js";
    import type { ConversationViewerApi } from "./components/ConversationViewer.svelte";
    import MessagesSidebar from "./components/MessagesSidebar.svelte";
    import MessagePanesHost from "./components/MessagePanesHost.svelte";
    import MessagesIngestDialog from "./components/MessagesIngestDialog.svelte";
    import MessagesMobileCompose from "./components/MessagesMobileCompose.svelte";

    type WindowApi = {
        get: (url: string, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        post: (url: string, body?: unknown, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        patch: (url: string, body?: unknown, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        delete: (url: string, config?: Record<string, unknown>) => Promise<{ data?: any }>;
        isCancel?: (e: unknown) => boolean;
    };

    function api(): WindowApi {
        return (window as unknown as { api: WindowApi }).api;
    }

    type Props = {
        destinationHash?: string | null;
        routeQuery?: Record<string, string>;
    };

    let { destinationHash = null, routeQuery = {} }: Props = $props();

    function snapshotGlobalConfig(): MessagesConfig {
        return GlobalState.config && typeof GlobalState.config === "object"
            ? { ...(GlobalState.config as MessagesConfig) }
            : {};
    }

    function getHashPopoutValue(): string | null {
        const hash = window.location.hash || "";
        const match = hash.match(/popout=([^&]+)/);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function detectPopout(): boolean {
        const path = window.location.hash || "";
        if (path.includes("/popout/")) {
            return true;
        }
        const q = routeQuery?.popout || getHashPopoutValue();
        return q === "conversation";
    }

    let config = $state<MessagesConfig>(snapshotGlobalConfig());
    let hasLoadedConversations = $state(false);
    let messagesListSidebarCollapsed = $state(loadFeatureSidebarCollapsed("messages") ?? false);
    let peers = $state<Record<string, Peer>>({});

    const initialPaneRestore = loadAndRestorePanes(destinationHash, 2);
    let panes = $state<Pane[]>(initialPaneRestore?.panes ?? [{ id: 1, peer: null }]);
    let focusedPaneId = $state(initialPaneRestore?.focusedPaneId ?? 1);
    let nextPaneId = $state(initialPaneRestore?.nextPaneId ?? 2);
    let paneFlex = $state<Record<number, number>>(initialPaneRestore?.paneFlex ?? {});
    let resizingPaneIds = $state<string | null>(null);
    let dragOverPaneId = $state<number | null>(null);
    let isDragOverAddZone = $state(false);
    let isWideViewport = $state(false);
    let isWideEnoughForThreePanes = $state(false);

    let conversations = $state<Conversation[]>([]);
    let conversationListSig = $state("");
    let announcesLoaded = $state(false);
    let folders = $state<Folder[]>([]);
    let selectedFolderId = $state<string | number | null>(null);
    const pageSize = 50;
    let hasMoreConversations = $state(true);
    let isLoadingMore = $state(false);
    let hasMoreAnnounces = $state(true);
    let isLoadingMoreAnnounces = $state(false);
    let isSearchingAnnounces = $state(false);
    let totalPeersCount = $state(0);
    let peersSearchTerm = $state("");
    let conversationSearchTerm = $state("");
    let filterUnreadOnly = $state(false);
    let filterFailedOnly = $state(false);
    let filterHasAttachmentsOnly = $state(false);
    let isLoadingConversations = $state(false);
    let pinnedPeerHashes = $state<string[]>([]);

    let isIngestModalOpen = $state(false);
    let ingestUri = $state("");
    let isMobileComposeModalOpen = $state(false);
    let mobileComposeAddress = $state("");

    let foldersImportInput: HTMLInputElement | null = $state(null);

    const paneViewers: Record<number, ConversationViewerApi | null> = {};
    let reloadInterval: ReturnType<typeof setInterval> | null = null;
    let conversationRefreshTimeout: ReturnType<typeof setTimeout> | null = null;
    let peersRefreshTimeout: ReturnType<typeof setTimeout> | null = null;
    let conversationsAbortController: AbortController | null = null;
    let announcesAbortController: AbortController | null = null;
    let stopIdentityReadyLoads: (() => void) | null = null;
    let liveTransportReadyWatch: (() => void) | null = null;
    let onConversationsVisibility: (() => void) | null = null;
    let resizeContext: {
        leftPaneId: number;
        rightPaneId: number;
        startX: number;
        leftWidth: number;
        combinedWidth: number;
        combinedFlex: number;
        minWidth: number;
    } | null = null;
    let boundPaneResizeMove: ((e: PointerEvent) => void) | null = null;
    let boundPaneResizeEnd: (() => void) | null = null;
    let paneViewportQuery: MediaQueryList | null = null;
    let threePaneViewportQuery: MediaQueryList | null = null;
    let paneViewportListener: ((e: MediaQueryListEvent) => void) | null = null;
    let threePaneViewportListener: ((e: MediaQueryListEvent) => void) | null = null;
    let destinationHashWatchReady = false;

    const isPopoutMode = $derived(detectPopout());
    const focusedPane = $derived(panes.find((pane) => pane.id === focusedPaneId) || panes[0] || null);
    const selectedPeer = $derived(focusedPane?.peer ?? null);
    const multiPaneEnabled = $derived(config?.messages_multi_pane_enabled !== false);
    const maxPanes = $derived(
        maxPanesFromWidth({
            isPopoutMode,
            isWideViewport,
            multiPaneEnabled,
            isWideEnoughForThreePanes,
        })
    );
    const visiblePanes = $derived(selectVisiblePanes({ panes, focusedPaneId, maxPanes }));
    const multiPaneActive = $derived(visiblePanes.length > 1);
    const canAddPane = $derived(!isPopoutMode && isWideViewport && panes.length < maxPanes && selectedPeer != null);
    const messagesSidebarPosition = $derived(
        config?.messages_sidebar_position === "right" ? ("right" as const) : ("left" as const)
    );
    const messagesSidebarOnRight = $derived(messagesSidebarPosition === "right");
    const paneLayoutSig = $derived(buildPaneLayoutSignature(panes, focusedPaneId));

    function setSelectedPeer(peer: Peer | null) {
        const pane = panes.find((p) => p.id === focusedPaneId) || panes[0];
        if (!pane) {
            return;
        }
        panes = panes.map((p) => (p.id === pane.id ? { ...p, peer } : p));
    }

    function messagesHash(dest?: string | null): string {
        const base = isPopoutMode ? "/popout/messages" : "/messages";
        const path = dest ? `${base}/${dest}` : base;
        const q =
            !isPopoutMode && routeQuery && Object.keys(routeQuery).length
                ? `?${new URLSearchParams(routeQuery).toString()}`
                : "";
        return `#${path}${q}`;
    }

    function replaceMessagesRoute(dest?: string | null) {
        location.hash = messagesHash(dest);
    }

    function syncUnreadCount() {
        const listIsPartial =
            hasMoreConversations ||
            filterUnreadOnly ||
            selectedFolderId != null ||
            Boolean(conversationSearchTerm && conversationSearchTerm.trim());
        if (listIsPartial) {
            GlobalEmitter.emit("notifications-changed");
            return;
        }
        GlobalState.unreadConversationsCount = countUnreadConversations(conversations);
    }

    function persistPanes() {
        persistPanesState({ panes, focusedPaneId, paneFlex, visiblePanes });
    }

    function syncOpenDestinationHashes() {
        const hashes = panes
            .map((pane) => pane.peer?.destination_hash)
            .filter((h): h is string => typeof h === "string" && h.length > 0);
        setOpenDestinationHashes(hashes);
        NotificationUtils.syncAndroidNotificationContext(hashes, Boolean(config?.do_not_disturb_enabled));
    }

    function registerPaneViewer(paneId: number, api: ConversationViewerApi | null) {
        if (api) {
            paneViewers[paneId] = api;
        } else {
            delete paneViewers[paneId];
        }
    }

    function startConversationsPollInterval() {
        if (reloadInterval) {
            clearInterval(reloadInterval);
            reloadInterval = null;
        }
        const pollMs = GlobalState.liveTransportReady ? 60000 : 15000;
        reloadInterval = setInterval(() => {
            if (typeof document !== "undefined" && document.visibilityState === "hidden") {
                return;
            }
            if (GlobalState.networkStarting && !GlobalState.networkReady && !GlobalState.networkDegraded) {
                return;
            }
            void getConversations();
            void getFolders();
        }, pollMs);
    }

    async function getConfig() {
        try {
            const response = await api().get(`/api/v1/config`);
            const next = response.data?.config;
            if (next && typeof next === "object") {
                mergeGlobalConfig(next);
                config = next;
            }
        } catch (e) {
            console.log(e);
            config = snapshotGlobalConfig();
        }
    }

    function onConfigEvent(json: { config?: MessagesConfig }) {
        const next = json?.config;
        if (next && typeof next === "object") {
            mergeGlobalConfig(next);
            config = next;
        }
    }

    function onAnnounceEvent(json: { announce?: Peer & { aspect?: string } }) {
        const aspect = json.announce?.aspect;
        if (aspect === "lxmf.delivery" && json.announce) {
            updatePeerFromAnnounce(peers, json.announce);
            peers = { ...peers };
        }
    }

    function requestConversationsRefresh() {
        if (conversationRefreshTimeout) {
            clearTimeout(conversationRefreshTimeout);
        }
        conversationRefreshTimeout = setTimeout(() => {
            void getConversations();
        }, 250);
    }

    function onLxmfDeliveryEvent() {
        requestConversationsRefresh();
    }

    function onLxmfMessageCreatedEvent(json: { lxmf_message?: Record<string, unknown> }) {
        if (json.lxmf_message) {
            applyOutboundMessageCreated(conversations, json.lxmf_message, {
                peers,
                selectedPeer,
                myLxmfAddressHash: config?.lxmf_address_hash || "",
                t,
            });
            conversations = [...conversations];
            const peerHash = json.lxmf_message.is_incoming
                ? (json.lxmf_message.source_hash as string)
                : (json.lxmf_message.destination_hash as string);
            if (peerHash) {
                void resolvePeerDisplayName(peerHash);
            }
        }
    }

    function onLxmfMessageStateUpdatedEvent(json: { lxmf_message?: Record<string, unknown> }) {
        if (json.lxmf_message) {
            applyOutboundMessageStateUpdated(conversations, json.lxmf_message);
            conversations = [...conversations];
        }
    }

    function onLxmfTelemetryEvent(json: { destination_hash?: string; is_tracking?: boolean }) {
        const destHash = json.destination_hash;
        if (!destHash) {
            return;
        }
        if (peers[destHash]) {
            peers = {
                ...peers,
                [destHash]: { ...peers[destHash], is_tracking: json.is_tracking },
            };
        }
        panes = applyPatchToPanePeers(panes, destHash, { is_tracking: json.is_tracking });
    }

    async function onLxmIngestUriResultEvent(json: {
        ingest_type?: string;
        map_query?: Record<string, string>;
        status?: string;
        destination_hash?: string;
    }) {
        if (json.ingest_type === "map_view" && json.map_query) {
            const mq = json.map_query;
            const entries: [string, string][] = [];
            if (mq.lat) entries.push(["lat", String(mq.lat)]);
            if (mq.lon) entries.push(["lon", String(mq.lon)]);
            if (mq.zoom) entries.push(["zoom", String(mq.zoom)]);
            if (mq.layers) entries.push(["layers", mq.layers]);
            if (mq.label) entries.push(["label", mq.label]);
            location.hash = `#/map?${new URLSearchParams(entries).toString()}`;
            return;
        }
        if (json.status === "success") {
            ingestUri = "";
            if (json.ingest_type === "lxma_contact" && json.destination_hash) {
                await onComposeNewMessage(json.destination_hash);
            } else {
                await getConversations();
            }
        }
    }

    async function getLxmfDeliveryAnnounces(append = false) {
        if (!append) {
            announcesLoaded = true;
        }
        let myController = announcesAbortController;
        try {
            if (!append) {
                announcesAbortController?.abort();
                announcesAbortController = new AbortController();
                myController = announcesAbortController;
                isSearchingAnnounces = true;
            } else if (!announcesAbortController) {
                announcesAbortController = new AbortController();
                myController = announcesAbortController;
            }
            const offset = append ? Object.keys(peers).length : 0;
            const response = await api().get(`/api/v1/announces`, {
                params: {
                    aspect: "lxmf.delivery",
                    limit: pageSize,
                    offset,
                    search: peersSearchTerm,
                },
                signal: myController?.signal,
            });
            const newAnnounces = response.data.announces || [];
            if (!append) {
                peers = {};
            }
            totalPeersCount = response.data.total_count || 0;
            for (const ann of newAnnounces) {
                updatePeerFromAnnounce(peers, ann);
            }
            peers = { ...peers };
            hasMoreAnnounces = newAnnounces.length === pageSize;
        } catch (e) {
            if (api().isCancel?.(e)) return;
            console.log(e);
        } finally {
            if (announcesAbortController === myController) {
                isLoadingMoreAnnounces = false;
                if (!append) {
                    isSearchingAnnounces = false;
                }
            }
        }
    }

    async function loadMoreAnnounces() {
        if (isLoadingMoreAnnounces || !hasMoreAnnounces) return;
        isLoadingMoreAnnounces = true;
        await getLxmfDeliveryAnnounces(true);
    }

    async function getLxmfDeliveryAnnounce(dest: string) {
        try {
            const response = await api().get(`/api/v1/announces`, {
                params: { destination_hash: dest, limit: 1 },
            });
            for (const ann of response.data.announces || []) {
                updatePeerFromAnnounce(peers, ann);
            }
            peers = { ...peers };
        } catch (e) {
            console.log(e);
        }
    }

    async function getConversations(append = false) {
        let myController = conversationsAbortController;
        try {
            if (!append) {
                conversationsAbortController?.abort();
                conversationsAbortController = new AbortController();
                myController = conversationsAbortController;
            } else if (!conversationsAbortController) {
                conversationsAbortController = new AbortController();
                myController = conversationsAbortController;
            }
            const shouldShowInitialLoading = !append && !hasLoadedConversations && conversations.length === 0;
            if (shouldShowInitialLoading) {
                isLoadingConversations = true;
            }
            const offset = append ? conversations.length : 0;
            const response = await api().get(`/api/v1/lxmf/conversations`, {
                params: {
                    ...buildConversationQueryParams({
                        conversationSearchTerm,
                        filterUnreadOnly,
                        filterFailedOnly,
                        filterHasAttachmentsOnly,
                        selectedFolderId,
                    }),
                    limit: pageSize,
                    offset,
                },
                signal: myController?.signal,
            });
            if (!response) {
                return;
            }
            const newConversations: Conversation[] = response.data.conversations || [];
            if (!append) {
                const nextSignature = conversationListSignature(newConversations);
                if (nextSignature === conversationListSig) {
                    hasLoadedConversations = true;
                    hasMoreConversations = newConversations.length === pageSize;
                    dismissUnreadForVisiblePanes();
                    return;
                }
            }
            if (append) {
                conversations = [...conversations, ...newConversations];
                conversationListSig = conversationListSignature(conversations);
            } else {
                const nextSignature = conversationListSignature(newConversations);
                if (nextSignature !== conversationListSig) {
                    conversationListSig = nextSignature;
                    if (conversations.length === 0) {
                        conversations = newConversations.slice();
                    } else {
                        const structureChanged = syncConversationListInPlace(conversations, newConversations);
                        if (!structureChanged) {
                            conversations = conversations.slice();
                        } else {
                            conversations = [...conversations];
                        }
                    }
                }
            }
            for (const conversation of newConversations) {
                updatePeerFromConversation(peers, conversation);
            }
            peers = { ...peers };
            hasLoadedConversations = true;
            hasMoreConversations = newConversations.length === pageSize;
            if (!append) {
                dismissUnreadForVisiblePanes();
            }
            syncUnreadCount();
        } catch (e) {
            if (api().isCancel?.(e)) return;
            console.log(e);
        } finally {
            if (conversationsAbortController === myController) {
                isLoadingConversations = false;
                isLoadingMore = false;
            }
        }
    }

    async function loadConversationPins() {
        try {
            const response = await api().get("/api/v1/lxmf/conversation-pins");
            pinnedPeerHashes = response.data.peer_hashes || [];
        } catch (e) {
            console.log(e);
        }
    }

    async function onToggleConversationPin(dest: string) {
        try {
            const response = await api().post("/api/v1/lxmf/conversation-pins/toggle", {
                destination_hash: dest,
            });
            pinnedPeerHashes = response.data.peer_hashes || [];
        } catch (e) {
            ToastUtils.error(t("messages.failed_toggle_pin"));
            console.log(e);
        }
    }

    async function resolvePeerDisplayName(peerHash: string) {
        try {
            const response = await api().get(`/api/v1/lxmf/conversations`, {
                params: { search: peerHash, limit: 1 },
            });
            const results = response.data.conversations || [];
            if (!results.length || results[0].destination_hash !== peerHash) {
                return;
            }
            const fresh = results[0];
            conversations = conversations.map((conv) => {
                if (conv.destination_hash !== peerHash) {
                    return conv;
                }
                return {
                    ...conv,
                    display_name:
                        fresh.display_name && fresh.display_name !== ANONYMOUS_PEER_DISPLAY_NAME
                            ? fresh.display_name
                            : conv.display_name,
                    custom_display_name: fresh.custom_display_name ?? conv.custom_display_name,
                    contact_image: fresh.contact_image ?? conv.contact_image,
                    lxmf_user_icon: fresh.lxmf_user_icon ?? conv.lxmf_user_icon,
                    is_contact: fresh.is_contact ?? conv.is_contact,
                };
            });
            panes = panes.map((pane) => {
                if (!pane.peer || pane.peer.destination_hash !== peerHash) {
                    return pane;
                }
                if (!shouldUpdatePanePeerDisplayName(fresh.display_name, pane.peer.display_name)) {
                    return pane;
                }
                return {
                    ...pane,
                    peer: {
                        ...pane.peer,
                        display_name: fresh.display_name,
                        custom_display_name: fresh.custom_display_name ?? pane.peer.custom_display_name,
                    },
                };
            });
        } catch {
            /* non-critical */
        }
    }

    async function getFolders() {
        try {
            const response = await api().get("/api/v1/lxmf/folders");
            folders = response.data || [];
        } catch (e) {
            if (!isRetryableHttpError(e)) {
                console.error("Failed to load folders", e);
            }
        }
    }

    async function onCreateFolder(name: string) {
        try {
            await api().post("/api/v1/lxmf/folders", { name });
            await getFolders();
            ToastUtils.success(t("messages.folder_created"));
        } catch {
            ToastUtils.error(t("messages.failed_create_folder"));
        }
    }

    async function onRenameFolder(payload: { id: string | number; name: string }) {
        try {
            await api().patch(`/api/v1/lxmf/folders/${payload.id}`, { name: payload.name });
            await getFolders();
            ToastUtils.success(t("messages.folder_renamed"));
        } catch {
            ToastUtils.error(t("messages.failed_rename_folder"));
        }
    }

    async function onDeleteFolder(id: string | number) {
        try {
            await api().delete(`/api/v1/lxmf/folders/${id}`);
            if (selectedFolderId === id) {
                selectedFolderId = null;
            }
            await getFolders();
            await getConversations();
            ToastUtils.success(t("messages.folder_deleted"));
        } catch {
            ToastUtils.error(t("messages.failed_delete_folder"));
        }
    }

    async function onMoveToFolder(payload: { peer_hashes: string[]; folder_id: string | number | null }) {
        try {
            const targetFolderId = payload.folder_id === 0 ? null : payload.folder_id;
            await api().post("/api/v1/lxmf/conversations/move-to-folder", {
                peer_hashes: payload.peer_hashes,
                folder_id: targetFolderId,
            });
            await getConversations();
            ToastUtils.success(t("messages.moved_to_folder"));
        } catch {
            ToastUtils.error(t("messages.failed_move_folder"));
        }
    }

    async function onBulkMarkAsRead(destination_hashes: string[]) {
        try {
            await api().post("/api/v1/lxmf/conversations/bulk-mark-as-read", { destination_hashes });
            GlobalEmitter.emit("notifications-changed");
            for (const h of destination_hashes || []) {
                NotificationUtils.clearMessageNotifications(h);
            }
            await getConversations();
            ToastUtils.success(t("messages.marked_read"));
        } catch {
            ToastUtils.error(t("messages.failed_mark_read"));
        }
    }

    async function onMarkAllAsRead() {
        try {
            await api().post("/api/v1/lxmf/conversations/bulk-mark-as-read", { mark_all: true });
            GlobalEmitter.emit("notifications-changed");
            NotificationUtils.clearAllMessageNotifications();
            await getConversations();
            ToastUtils.success(t("messages.marked_all_read"));
        } catch {
            ToastUtils.error(t("messages.failed_mark_read"));
        }
    }

    async function onBulkDelete(destination_hashes: string[]) {
        try {
            const confirmed = await DialogUtils.confirm(
                t("messages.delete_conversations_confirm"),
                t("messages.delete_conversations_title")
            );
            if (!confirmed) return;
            await api().post("/api/v1/lxmf/conversations/bulk-delete", { destination_hashes });
            await getConversations();
            ToastUtils.success(t("messages.conversations_deleted"));
        } catch {
            ToastUtils.error(t("messages.failed_delete_conversations"));
        }
    }

    async function onExportFolders() {
        try {
            const response = await api().get("/api/v1/lxmf/folders/export");
            const data = JSON.stringify(response.data, null, 2);
            const blob = new Blob([data], { type: "application/json" });
            await DownloadUtils.downloadFile(`meshchatx-folders-${new Date().toISOString().slice(0, 10)}.json`, blob);
        } catch {
            ToastUtils.error(t("messages.failed_export_folders"));
        }
    }

    function onImportFolders() {
        foldersImportInput?.click();
    }

    function onFoldersImportFileSelected(event: Event) {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        target.value = "";
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (re) => {
            try {
                const data = JSON.parse(String((re.target as FileReader).result));
                await api().post("/api/v1/lxmf/folders/import", data);
                await getFolders();
                await getConversations();
                ToastUtils.success(t("messages.folders_imported"));
            } catch {
                ToastUtils.error(t("messages.failed_import_folders"));
            }
        };
        reader.readAsText(file);
    }

    async function loadMoreConversations() {
        if (isLoadingMore || !hasMoreConversations) return;
        isLoadingMore = true;
        await getConversations(true);
    }

    function onPeerClick(peer: Peer) {
        setSelectedPeer(peer);
        replaceMessagesRoute(peer.destination_hash);
    }

    function onConversationClick(conversation: Conversation) {
        onPeerClick(conversation);
        const viewer = paneViewers[focusedPaneId];
        viewer?.markConversationAsRead?.(conversation);
    }

    function dismissUnreadForOpenDestination(dest: string) {
        const normalized = Utils.normalizeMeshchatHashHex(dest || "");
        if (!normalized) {
            return;
        }
        const conversation = findUnreadTarget(normalized, conversations, panes, selectedPeer);
        if (!conversation) {
            return;
        }
        const viewer = paneViewers[focusedPaneId] || Object.values(paneViewers).find((v) => v?.markConversationAsRead);
        if (viewer?.markConversationAsRead) {
            void viewer.markConversationAsRead(conversation, { force: true });
            return;
        }
        const wasUnread = applyOptimisticUnreadClear(conversation);
        conversations = [...conversations];
        Promise.resolve(api().post(`/api/v1/lxmf/conversations/${normalized}/mark-as-read`))
            .then(() => {
                GlobalEmitter.emit("notifications-changed");
                NotificationUtils.clearMessageNotifications(normalized);
                GlobalState.unreadConversationsCount = nextUnreadConversationsCount(
                    GlobalState.unreadConversationsCount,
                    wasUnread
                );
            })
            .catch(() => {
                revertOptimisticUnreadClear(conversation, wasUnread);
                conversations = [...conversations];
            });
    }

    function dismissUnreadForVisiblePanes(opts: { force?: boolean } = {}) {
        for (const normalized of destinationsNeedingUnreadDismiss(panes, conversations, opts.force)) {
            dismissUnreadForOpenDestination(normalized);
        }
    }

    async function onComposeNewMessage(destHash: string | null | undefined) {
        if (destHash == null) {
            if (selectedPeer) {
                return;
            }
            queueMicrotask(() => {
                document.getElementById("compose-input")?.focus();
            });
            return;
        }
        const destinationHashNorm = Utils.normalizeMeshchatHashHex(destHash);
        await getLxmfDeliveryAnnounce(destinationHashNorm);
        const existingPeer = peers[destinationHashNorm];
        if (existingPeer) {
            onPeerClick(existingPeer);
            dismissUnreadForOpenDestination(destinationHashNorm);
            return;
        }
        if (destinationHashNorm.length !== 32) {
            DialogUtils.alert(t("common.invalid_address"));
            return;
        }
        const existingConversation = conversations.find(
            (c) => Utils.normalizeMeshchatHashHex(c.destination_hash) === destinationHashNorm
        );
        onPeerClick({
            display_name: existingConversation?.display_name ?? ANONYMOUS_PEER_DISPLAY_NAME,
            custom_display_name: existingConversation?.custom_display_name ?? null,
            destination_hash: destinationHashNorm,
            is_unread: existingConversation?.is_unread === true,
        });
        dismissUnreadForOpenDestination(destinationHashNorm);
    }

    function onCloseConversationViewer() {
        setSelectedPeer(null);
        if (isPopoutMode) {
            window.close();
            return;
        }
        replaceMessagesRoute(null);
    }

    function syncRouteToFocusedPane() {
        replaceMessagesRoute(selectedPeer?.destination_hash || null);
    }

    function focusPane(paneId: number) {
        if (panes.some((pane) => pane.id === paneId)) {
            focusedPaneId = paneId;
        }
    }

    function addPane() {
        const existingEmpty = panes.find((pane) => !pane.peer);
        if (existingEmpty) {
            focusedPaneId = existingEmpty.id;
            return;
        }
        if (!canAddPane) {
            return;
        }
        const id = nextPaneId++;
        panes = [...panes, { id, peer: null }];
        focusedPaneId = id;
    }

    function peerFromDestinationHash(dest: string): Peer {
        const conversation = conversations.find((c) => c.destination_hash === dest);
        if (conversation) {
            return conversation;
        }
        const peer = peers[dest];
        if (peer) {
            return peer;
        }
        return {
            destination_hash: dest,
            display_name: ANONYMOUS_PEER_DISPLAY_NAME,
            custom_display_name: null,
        };
    }

    function openConversationInPane(paneId: number, dest: string) {
        const normalized = Utils.normalizeMeshchatHashHex(dest || "");
        if (normalized.length !== 32) {
            return;
        }
        focusedPaneId = paneId;
        const peer = peerFromDestinationHash(normalized);
        onPeerClick(peer);
        paneViewers[paneId]?.markConversationAsRead?.(peer);
    }

    function onPaneClose(paneId: number) {
        const index = panes.findIndex((pane) => pane.id === paneId);
        if (index === -1) {
            return;
        }
        if (panes.length > 1) {
            const next = panes.slice();
            next.splice(index, 1);
            panes = next;
            const { [paneId]: _removed, ...restFlex } = paneFlex;
            paneFlex = restFlex;
            delete paneViewers[paneId];
            if (panes.length === 1) {
                paneFlex = { ...paneFlex, [panes[0].id]: 1 };
            }
            if (focusedPaneId === paneId) {
                const neighbour = panes[index] || panes[index - 1] || panes[0];
                focusedPaneId = neighbour.id;
            }
            syncRouteToFocusedPane();
            return;
        }
        onCloseConversationViewer();
    }

    function startPaneResize(event: PointerEvent, leftPaneId: number, rightPaneId: number) {
        if (!isWideViewport || (event.button != null && event.button !== 0)) {
            return;
        }
        const resizer = event.currentTarget as HTMLElement | null;
        const leftEl = resizer?.previousElementSibling as HTMLElement | null;
        const rightEl = resizer?.nextElementSibling as HTMLElement | null;
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
        const leftFlex =
            typeof paneFlex[leftPaneId] === "number" && paneFlex[leftPaneId] > 0 ? paneFlex[leftPaneId] : 1;
        const rightFlex =
            typeof paneFlex[rightPaneId] === "number" && paneFlex[rightPaneId] > 0 ? paneFlex[rightPaneId] : 1;
        resizeContext = {
            leftPaneId,
            rightPaneId,
            startX: event.clientX,
            leftWidth,
            combinedWidth,
            combinedFlex: leftFlex + rightFlex,
            minWidth: Math.min(220, combinedWidth / 2),
        };
        resizingPaneIds = `${leftPaneId}:${rightPaneId}`;
        boundPaneResizeMove = onPaneResizeMove;
        boundPaneResizeEnd = endPaneResize;
        window.addEventListener("pointermove", boundPaneResizeMove);
        window.addEventListener("pointerup", boundPaneResizeEnd);
        document.body.style.userSelect = "none";
        document.body.style.cursor = "col-resize";
    }

    function onPaneResizeMove(event: PointerEvent) {
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
        paneFlex = {
            ...paneFlex,
            [ctx.leftPaneId]: leftFlex,
            [ctx.rightPaneId]: ctx.combinedFlex - leftFlex,
        };
    }

    function endPaneResize() {
        if (boundPaneResizeMove) {
            window.removeEventListener("pointermove", boundPaneResizeMove);
        }
        if (boundPaneResizeEnd) {
            window.removeEventListener("pointerup", boundPaneResizeEnd);
        }
        boundPaneResizeMove = null;
        boundPaneResizeEnd = null;
        resizeContext = null;
        resizingPaneIds = null;
        document.body.style.userSelect = "";
        document.body.style.cursor = "";
        persistPanes();
    }

    function resetPaneSizes() {
        const next: Record<number, number> = {};
        for (const pane of panes) {
            next[pane.id] = 1;
        }
        paneFlex = next;
        persistPanes();
    }

    function onOutboundComposeEnqueued(payload: Record<string, unknown>) {
        applyOutboundComposeEnqueued(conversations, payload as { peerHash: string }, {
            peers,
            selectedPeer,
            myLxmfAddressHash: config?.lxmf_address_hash || "",
            t,
        });
        conversations = [...conversations];
        const peerHash = payload.peerHash as string | undefined;
        if (peerHash) {
            void resolvePeerDisplayName(peerHash);
        }
    }

    function onIdentitySwitched() {
        conversationsAbortController?.abort();
        conversations = [];
        conversationListSig = "";
        hasMoreConversations = true;
        hasLoadedConversations = false;
        announcesLoaded = false;
        folders = [];
        selectedFolderId = null;
        panes = panes.map((pane) => ({ ...pane, peer: null }));
        peers = {};
        persistPanes();
        void getConfig();
        void getConversations();
        void getFolders();
        void loadConversationPins();
    }

    async function ingestPaperMessage() {
        if (!ingestUri) return;
        try {
            WebSocketConnection.send(JSON.stringify({ type: "lxm.ingest_uri", uri: ingestUri }));
            isIngestModalOpen = false;
        } catch {
            ToastUtils.error(t("messages.failed_send_ingest"));
        }
    }

    function setupPaneViewportWatchers() {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            isWideViewport = false;
            isWideEnoughForThreePanes = false;
            return;
        }
        paneViewportQuery = window.matchMedia("(min-width: 768px)");
        isWideViewport = paneViewportQuery.matches;
        paneViewportListener = (event) => {
            isWideViewport = event.matches;
        };
        paneViewportQuery.addEventListener("change", paneViewportListener);
        threePaneViewportQuery = window.matchMedia("(min-width: 1280px)");
        isWideEnoughForThreePanes = threePaneViewportQuery.matches;
        threePaneViewportListener = (event) => {
            isWideEnoughForThreePanes = event.matches;
        };
        threePaneViewportQuery.addEventListener("change", threePaneViewportListener);
    }

    function teardownPaneViewportWatchers() {
        if (paneViewportQuery && paneViewportListener) {
            paneViewportQuery.removeEventListener("change", paneViewportListener);
        }
        if (threePaneViewportQuery && threePaneViewportListener) {
            threePaneViewportQuery.removeEventListener("change", threePaneViewportListener);
        }
    }

    $effect(() => {
        saveFeatureSidebarCollapsed("messages", messagesListSidebarCollapsed);
    });

    $effect(() => {
        void paneLayoutSig;
        persistPanes();
        syncOpenDestinationHashes();
    });

    $effect(() => {
        const newHash = destinationHash;
        if (!destinationHashWatchReady) {
            return;
        }
        if (!newHash) {
            return;
        }
        isMobileComposeModalOpen = false;
        const currentHash = selectedPeer?.destination_hash;
        const normalizedNew = Utils.normalizeMeshchatHashHex(newHash);
        if (currentHash && Utils.normalizeMeshchatHashHex(currentHash) === normalizedNew) {
            dismissUnreadForOpenDestination(normalizedNew);
            return;
        }
        void onComposeNewMessage(newHash);
    });

    onMount(() => {
        syncOpenDestinationHashes();
        setupPaneViewportWatchers();

        onWsEvent("config", onConfigEvent);
        onWsEvent("announce", onAnnounceEvent);
        onWsEvent("lxmf.delivery", onLxmfDeliveryEvent);
        onWsEvent("lxmf_message_created", onLxmfMessageCreatedEvent);
        onWsEvent("lxmf_message_state_updated", onLxmfMessageStateUpdatedEvent);
        onWsEvent("lxmf.telemetry", onLxmfTelemetryEvent);
        onWsEvent("lxm.ingest_uri.result", onLxmIngestUriResultEvent);
        GlobalEmitter.on("compose-new-message", onComposeNewMessage);
        GlobalEmitter.on("refresh-conversations", requestConversationsRefresh);
        GlobalEmitter.on("websocket-reconnected", requestConversationsRefresh);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);

        stopIdentityReadyLoads = runWhenIdentityHttpReady(() => {
            void getConfig();
            void getConversations();
            void loadConversationPins();
            void getFolders();
        });

        startConversationsPollInterval();
        let lastReady = GlobalState.liveTransportReady;
        liveTransportReadyWatch = () => {
            const ready = GlobalState.liveTransportReady;
            if (ready !== lastReady) {
                lastReady = ready;
                startConversationsPollInterval();
            }
        };
        const livePoll = setInterval(liveTransportReadyWatch, 2000);

        onConversationsVisibility = () => {
            if (typeof document !== "undefined" && document.visibilityState === "visible") {
                requestConversationsRefresh();
            }
        };
        document.addEventListener("visibilitychange", onConversationsVisibility);

        if (destinationHash) {
            void onComposeNewMessage(destinationHash);
        } else if (selectedPeer?.destination_hash) {
            dismissUnreadForVisiblePanes({ force: true });
            syncRouteToFocusedPane();
        }
        destinationHashWatchReady = true;

        return () => {
            clearInterval(reloadInterval || undefined);
            clearInterval(livePoll);
            clearTimeout(conversationRefreshTimeout || undefined);
            clearTimeout(peersRefreshTimeout || undefined);
            stopIdentityReadyLoads?.();
            if (onConversationsVisibility) {
                document.removeEventListener("visibilitychange", onConversationsVisibility);
            }
            conversationsAbortController?.abort();
            announcesAbortController?.abort();
            endPaneResize();
            teardownPaneViewportWatchers();
            setOpenDestinationHashes([]);
            offWsEvent("config", onConfigEvent);
            offWsEvent("announce", onAnnounceEvent);
            offWsEvent("lxmf.delivery", onLxmfDeliveryEvent);
            offWsEvent("lxmf_message_created", onLxmfMessageCreatedEvent);
            offWsEvent("lxmf_message_state_updated", onLxmfMessageStateUpdatedEvent);
            offWsEvent("lxmf.telemetry", onLxmfTelemetryEvent);
            offWsEvent("lxm.ingest_uri.result", onLxmIngestUriResultEvent);
            GlobalEmitter.off("compose-new-message", onComposeNewMessage);
            GlobalEmitter.off("refresh-conversations", requestConversationsRefresh);
            GlobalEmitter.off("websocket-reconnected", requestConversationsRefresh);
            GlobalEmitter.off("identity-switched", onIdentitySwitched);
        };
    });
</script>

<div class="flex flex-1 min-w-0 h-full overflow-hidden {messagesSidebarOnRight ? 'flex-row-reverse' : ''}">
    <input
        bind:this={foldersImportInput}
        type="file"
        accept=".json,application/json"
        class="sr-only absolute m-[-1px] h-px w-px overflow-hidden border-0 p-0 whitespace-nowrap"
        tabindex="-1"
        aria-hidden="true"
        onchange={onFoldersImportFileSelected}
    />

    {#if !isPopoutMode}
        <MessagesSidebar
            class={destinationHash ? "hidden sm:flex" : ""}
            sidebarPosition={messagesSidebarPosition}
            collapsed={messagesListSidebarCollapsed}
            {conversations}
            {peers}
            {folders}
            {selectedFolderId}
            selectedDestinationHash={selectedPeer?.destination_hash || ""}
            {conversationSearchTerm}
            {filterUnreadOnly}
            {filterFailedOnly}
            {filterHasAttachmentsOnly}
            isLoading={isLoadingConversations}
            {isLoadingMore}
            {hasMoreConversations}
            {isLoadingMoreAnnounces}
            {isSearchingAnnounces}
            {hasMoreAnnounces}
            {peersSearchTerm}
            {totalPeersCount}
            {pinnedPeerHashes}
            onconversationClick={onConversationClick}
            onpeerClick={onPeerClick}
            onconversationSearchChanged={(term) => {
                conversationSearchTerm = term;
                requestConversationsRefresh();
            }}
            onconversationFilterChanged={(filterKey) => {
                if (filterKey === "unread") filterUnreadOnly = !filterUnreadOnly;
                else if (filterKey === "failed") filterFailedOnly = !filterFailedOnly;
                else if (filterKey === "attachments") filterHasAttachmentsOnly = !filterHasAttachmentsOnly;
                requestConversationsRefresh();
            }}
            onpeersSearchChanged={(term) => {
                peersSearchTerm = term;
                isSearchingAnnounces = true;
                if (peersRefreshTimeout) clearTimeout(peersRefreshTimeout);
                peersRefreshTimeout = setTimeout(() => {
                    void getLxmfDeliveryAnnounces();
                }, 500);
            }}
            oningestPaperMessage={() => {
                ingestUri = "";
                isIngestModalOpen = true;
            }}
            onloadMore={() => void loadMoreConversations()}
            onloadMoreAnnounces={() => void loadMoreAnnounces()}
            onannouncesTabActivated={() => {
                if (!announcesLoaded) {
                    announcesLoaded = true;
                    void getLxmfDeliveryAnnounces();
                }
            }}
            onfolderClick={(folderId) => {
                selectedFolderId = folderId;
                requestConversationsRefresh();
            }}
            oncreateFolder={(name) => void onCreateFolder(name)}
            onrenameFolder={(payload) => void onRenameFolder(payload)}
            ondeleteFolder={(id) => void onDeleteFolder(id)}
            onmoveToFolder={(payload) => void onMoveToFolder(payload)}
            onbulkMarkAsRead={(hashes) => void onBulkMarkAsRead(hashes)}
            onmarkAllAsRead={() => void onMarkAllAsRead()}
            onbulkDelete={(hashes) => void onBulkDelete(hashes)}
            onexportFolders={() => void onExportFolders()}
            onimportFolders={onImportFolders}
            onmessagesImported={() => void getConversations()}
            ontoggleConversationPin={(hash) => void onToggleConversationPin(hash)}
            ontoggleCollapse={() => {
                messagesListSidebarCollapsed = !messagesListSidebarCollapsed;
            }}
        />
    {/if}

    <div class="flex flex-1 overflow-hidden min-w-0 bg-sem-canvas {destinationHash ? 'flex' : 'hidden sm:flex'}">
        <MessagePanesHost
            {visiblePanes}
            {focusedPaneId}
            {multiPaneActive}
            {canAddPane}
            {paneFlex}
            {resizingPaneIds}
            {dragOverPaneId}
            {isDragOverAddZone}
            {config}
            {conversations}
            isPopout={isPopoutMode}
            onfocusPane={focusPane}
            onaddPane={addPane}
            onstartPaneResize={startPaneResize}
            onresetPaneSizes={resetPaneSizes}
            onpaneDragOver={(paneId) => {
                if (isWideViewport) dragOverPaneId = paneId;
            }}
            onpaneDragLeave={(paneId) => {
                if (dragOverPaneId === paneId) dragOverPaneId = null;
            }}
            onpaneDrop={(paneId, event) => {
                dragOverPaneId = null;
                const hash = event?.dataTransfer?.getData("text/plain");
                if (hash) openConversationInPane(paneId, hash);
            }}
            onaddZoneDragOver={() => {
                if (canAddPane) isDragOverAddZone = true;
            }}
            onaddZoneDragLeave={() => {
                isDragOverAddZone = false;
            }}
            onaddZoneDrop={(event) => {
                isDragOverAddZone = false;
                const hash = event?.dataTransfer?.getData("text/plain");
                if (!hash || panes.length >= maxPanes) return;
                const id = nextPaneId++;
                panes = [...panes, { id, peer: null }];
                openConversationInPane(id, hash);
            }}
            onpanePeerUpdate={(paneId, peer) => {
                focusPane(paneId);
                if (peer) onPeerClick(peer);
            }}
            onpaneClose={onPaneClose}
            onupdatePeerTracking={({ destination_hash, is_tracking }) => {
                if (peers[destination_hash]) {
                    peers = {
                        ...peers,
                        [destination_hash]: { ...peers[destination_hash], is_tracking },
                    };
                }
                panes = applyPatchToPanePeers(panes, destination_hash, { is_tracking });
            }}
            onreloadConversations={requestConversationsRefresh}
            onoutboundComposeEnqueued={onOutboundComposeEnqueued}
            onregisterPaneViewer={registerPaneViewer}
        />
    </div>

    {#if !isPopoutMode && !destinationHash}
        <button
            type="button"
            class="sm:hidden fixed z-65 flex h-14 w-14 items-center justify-center rounded-full bg-zinc-900 text-white shadow-lg ring-1 ring-white/10 transition active:scale-95 dark:bg-zinc-100 dark:text-zinc-900 dark:ring-zinc-800 right-[max(1rem,env(safe-area-inset-right,0px))] bottom-[max(1.25rem,env(safe-area-inset-bottom,0px))]"
            title={t("app.compose")}
            onclick={() => {
                mobileComposeAddress = "";
                isMobileComposeModalOpen = true;
            }}
        >
            <MaterialDesignIcon iconName="plus" class="size-7" />
        </button>
    {/if}

    <MessagesMobileCompose
        open={isMobileComposeModalOpen}
        address={mobileComposeAddress}
        onclose={() => {
            isMobileComposeModalOpen = false;
        }}
        onupdateAddress={(v) => {
            mobileComposeAddress = v;
        }}
        onsubmit={() => {
            const raw = mobileComposeAddress.trim();
            if (!raw) return;
            isMobileComposeModalOpen = false;
            mobileComposeAddress = "";
            void onComposeNewMessage(raw);
        }}
        oningest={() => {
            isMobileComposeModalOpen = false;
            ingestUri = "";
            isIngestModalOpen = true;
        }}
    />

    <MessagesIngestDialog
        open={isIngestModalOpen}
        {ingestUri}
        onclose={() => {
            isIngestModalOpen = false;
        }}
        onupdateIngestUri={(v) => {
            ingestUri = v;
        }}
        oningest={() => void ingestPaperMessage()}
    />
</div>
