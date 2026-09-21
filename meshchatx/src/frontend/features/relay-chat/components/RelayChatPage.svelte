<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy, tick } from "svelte";
    import { onClickOutside } from "runed";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import GlobalState from "../../../js/GlobalState.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import Utils from "../../../js/Utils.js";
    import MarkdownRenderer from "../../../js/MarkdownRenderer.js";
    import { t } from "../../../js/i18n.js";
    import { apiPath, EMITTER_EVENTS, STORAGE_KEYS, WS_EVENTS } from "../../../js/constants.js";
    import { onWsEvent, offWsEvent } from "../../../js/registries/wsEventRegistry.js";
    import { getCurrentRoute, navigate } from "../../../shell/hashRouter.js";
    import { countRelayMentions } from "../../../js/relayMentionCount.js";
    import { unjoinedAvailableRooms } from "../../../js/rrcAvailableRooms.js";
    import { copyTextToClipboard } from "../../../js/clipboardUtils.js";
    import {
        buildRelayMessageTimeline,
        filterUniqueOlderRelayMessages,
        isRelayPeerJoinPartMessage,
        mergeRelayMessages,
        relayMessageAlreadyPresent,
        relayMessageKey,
        RELAY_MESSAGES_INITIAL_PAGE_SIZE,
        RELAY_MESSAGES_PREVIOUS_PAGE_SIZE,
    } from "../../../js/relayMessageTimeline.js";
    import { relayNickCompletionStep } from "../../../js/relay/relayNickCompletion.js";
    import { filterRelayMessages } from "../../../js/relayMessageSearch.js";
    import {
        isIgnoredRelayMessage,
        loadRelayPrefs,
        relayPrefsEqualIgnored,
        saveRelayPrefs,
    } from "../../../js/relay/relayPrefsStore.js";
    import { normalizeHighlightWordInput, relayTextMatchesWords } from "../../../js/relay/relayHighlights.js";
    import { loadRelayLayout, saveRelayLayout } from "../../../js/relayLayoutStore.js";
    import { loadFeatureSidebarCollapsed, saveFeatureSidebarCollapsed } from "../../../js/browserLayoutStore.js";
    import {
        applyRelayShareLink,
        buildRelayShareMessage,
        parseRelayUri,
        RRC_HUB_ASPECT,
    } from "../../../js/relayLinkUtils.js";
    import { handleRichHtmlLinkClick } from "../../../js/NomadRichHtmlLinks.js";
    import { preferNativeTextSelectionMenu } from "../../../js/contextMenuUtils.js";
    import { useIdentityScope } from "../../../js/identityScope.js";
    import { loadDraft, saveDraft } from "../../messages/lib/conversationDrafts.js";
    import * as TranslationService from "../../../js/TranslationService.js";
    import RelayChatHeader from "./RelayChatHeader.svelte";
    import RelayHubSidebar from "./RelayHubSidebar.svelte";
    import RelayMembersPanel from "./RelayMembersPanel.svelte";
    import RelaySearchPanel from "./RelaySearchPanel.svelte";
    import RelayMessageComposer from "./RelayMessageComposer.svelte";
    import RelayMessageEntry from "./RelayMessageEntry.svelte";
    import RelayMessageListVirtual from "./RelayMessageListVirtual.svelte";
    import RelayDiscoveryView from "./RelayDiscoveryView.svelte";
    import RelayHostView from "./RelayHostView.svelte";
    import RelayHostModerationPage from "./RelayHostModerationPage.svelte";
    import RelayBotsPage from "./RelayBotsPage.svelte";
    import RelaySearchPage from "./RelaySearchPage.svelte";
    import RelayChatModals from "./RelayChatModals.svelte";
    import {
        displayName,
        formatTime,
        hubDisplayName,
        isHubConnected,
        nameStyle,
        orderedKnownRoomNames,
    } from "../lib/relayFormatters.js";
    import { MIN_VIRTUAL_RELAY_ENTRIES } from "../lib/relayVirtual.js";
    import type {
        RrcAvailableRoom,
        RrcDiscoveredHub,
        RrcHostedHub,
        RrcHub,
        RrcIgnoredPeer,
        RrcKnownHub,
        RrcMember,
        RrcMessage,
        RrcMessageTranslation,
        RrcRoom,
        RrcTimelineEntry,
    } from "../lib/types.js";

    interface Props {
        hubHash?: string | null;
        room?: string | null;
        isPopout?: boolean;
        routeQuery?: Record<string, string>;
    }

    let { hubHash = null, room = null, isPopout = false, routeQuery = {} }: Props = $props();

    type RelayView = "chat" | "discovery" | "host" | "bots" | "search";

    // Matches the conversations jump-to-bottom threshold: within this many
    // pixels of the newest message the view still auto-follows live arrivals.
    const RELAY_NEAR_BOTTOM_PX = 80;
    const LOAD_PREVIOUS_SCROLL_EDGE_PX = 200;
    // Bounds the in-memory window during deep scroll-back. Dropped tail entries
    // are refetched when the user scrolls back to the newest edge.
    const MAX_RELAY_MESSAGES = 2000;
    const DEFAULT_ANNOUNCE_INTERVAL_SECONDS = 900;

    const isPopoutMode = $derived(isPopout === true || getCurrentRoute()?.meta?.isPopout === true);

    const tabs = [
        { id: "chat", label: "relay_chat.tab_chat", icon: "forum" },
        { id: "discovery", label: "relay_chat.tab_discovery", icon: "compass" },
        { id: "host", label: "relay_chat.tab_host", icon: "server" },
        { id: "bots", label: "relay_chat.tab_bots", icon: "robot" },
        { id: "search", label: "relay_chat.tab_search", icon: "magnify" },
    ] as const;

    // Below md these collapse into the overflow menu so the tab bar never
    // scrolls horizontally on phones. Chat and Discovery stay pinned.
    const OVERFLOW_TAB_IDS = new Set<string>(["host", "bots", "search"]);
    const overflowTabs = tabs.filter((tab) => OVERFLOW_TAB_IDS.has(tab.id));

    let view = $state<RelayView>("chat");
    let viewBeforeRoomOpen = $state<RelayView | null>(null);
    let overflowMenuOpen = $state(false);
    let overflowMenuEl: HTMLDivElement | undefined = $state();
    onClickOutside(
        () => overflowMenuEl,
        () => {
            overflowMenuOpen = false;
        }
    );

    function handleOverflowKeydown(e: KeyboardEvent) {
        if (e.key === "Escape" && overflowMenuOpen) {
            overflowMenuOpen = false;
        }
    }

    // Hubs, rooms, messages
    let hubs = $state<RrcHub[]>([]);
    let selectedHubHash = $state<string | null>(null);
    let selectedRoom = $state<string | null>(null);
    let expandedHubs = $state<Record<string, boolean>>({});
    let availableRoomsExpanded = $state<Record<string, boolean>>({});
    let availableRoomsRefreshing = $state<Record<string, boolean>>({});
    let messages = $state<RrcMessage[]>([]);
    let members = $state<RrcMember[]>([]);
    let hasMorePrevious = $state(false);
    let isLoadingPrevious = $state(false);
    let expandedPresenceGroups = $state<Record<string, boolean>>({});
    let tailTrimmed = $state(false);

    let roomSelectSequence = 0;
    let loadPreviousInFlight = 0;
    let reloadingLatest = false;
    let headTrimQueued = false;

    // Discovery
    let discovered = $state<RrcDiscoveredHub[]>([]);
    let discoverySearch = $state("");
    let discoveryLoading = $state(false);
    let discoverySearchTimer: ReturnType<typeof setTimeout> | null = null;

    // Hosting
    let serverHubs = $state<RrcHostedHub[]>([]);
    let hostModeration = $state<{ hub: RrcHostedHub | null; tab: "rooms" | "members"; room: string | null }>({
        hub: null,
        tab: "rooms",
        room: null,
    });
    let hostUptimeTick = $state(0);
    let hostUptimeAnchorMs = 0;
    let hostUptimeTimer: ReturnType<typeof setInterval> | null = null;

    // Layout
    let relaySidebarCollapsed = $state(loadFeatureSidebarCollapsed("relayChat") ?? false);
    let smUp = $state(false);
    let smMq: MediaQueryList | null = null;
    let showMembers = $state(false);
    let showSearch = $state(false);
    let messageSearch = $state("");
    let memberDmLoadingHash = $state<string | null>(null);
    let joinRoomName = $state("");
    let joinRoomKey = $state("");

    // Menus and modals
    let sidebarMenu = $state<{ show: boolean; x: number; y: number; hub: RrcHub | null; room: string | null }>({
        show: false,
        x: 0,
        y: 0,
        hub: null,
        room: null,
    });
    let messageMenu = $state<{ show: boolean; x: number; y: number; msg: RrcMessage | null }>({
        show: false,
        x: 0,
        y: 0,
        msg: null,
    });
    let showAddHub = $state(false);
    let showHubSettings = $state(false);
    let showChatPrefs = $state(false);
    let showCreateHub = $state(false);
    let showHostHubSettings = $state(false);
    let settingsHubHash = $state<string | null>(null);
    let hostHubSettingsId = $state<string | null>(null);
    let applyingOptionsToAllHubs = $state(false);

    // Composer, scroll, prefs
    let composer = $state("");
    let sending = $state(false);
    let relayAtBottom = $state(true);
    let newMessagesBelow = $state(0);
    let nickCycle = $state<Record<string, unknown> | null>(null);
    let ignoredPeers = $state<RrcIgnoredPeer[]>([]);
    let highlightWords = $state<string[]>([]);
    let hideJoinPart = $state(false);
    let localMentionRooms = $state<Record<string, string[]>>({});
    let badKeyPromptInFlight: string | null = null;

    // Translation
    let translationPacks = $state<{ pair: string }[]>([]);
    let messageTranslations = $state<Record<string, RrcMessageTranslation>>({});

    let scrollContainerEl = $state<HTMLDivElement | null>(null);
    let virtualListComp = $state<{
        scrollToBottom?: () => void;
        scrollToMessageKey?: (key: string) => void;
    } | null>(null);
    let composerComp = $state<{ focus?: () => void } | null>(null);

    const identityScope = useIdentityScope({
        getIdentityKey: () => {
            const hash = GlobalState.config?.identity_hash;
            return typeof hash === "string" && hash ? hash : "_";
        },
    });

    const rrcEnabled = $derived(GlobalState.config?.rrc_enabled !== false);
    const showUnreadBadges = $derived(GlobalState.config?.rrc_unread_badges_enabled !== false);
    const effectiveSidebarCollapsed = $derived(relaySidebarCollapsed && smUp && !isPopoutMode);

    const overflowViewTab = $derived(overflowTabs.find((tab) => tab.id === view) || null);
    const isOverflowView = $derived(overflowViewTab !== null);
    const overflowViewIcon = $derived(overflowViewTab?.icon || "dots-horizontal");

    const selectedHub = $derived.by((): RrcHub | null => {
        return hubs.find((h) => h.hub_hash === selectedHubHash) || null;
    });

    const settingsHub = $derived.by((): RrcHub | null => {
        if (!settingsHubHash) return null;
        return hubs.find((h) => h.hub_hash === settingsHubHash) || null;
    });

    const hostSettingsHub = $derived.by((): RrcHostedHub | null => {
        if (!hostHubSettingsId) return null;
        return serverHubs.find((h) => h.id === hostHubSettingsId) || null;
    });

    const canModerateSelectedHub = $derived.by(() => {
        if (!selectedHub) return false;
        return serverHubs.some((s) => s.running && s.dest_hash === selectedHub.hub_hash);
    });

    const botsKnownHubs = $derived.by((): RrcKnownHub[] => {
        const seen = new Set<string>();
        const out: RrcKnownHub[] = [];
        for (const h of serverHubs) {
            if (h.dest_hash && !seen.has(h.dest_hash)) {
                seen.add(h.dest_hash);
                out.push({ hash: h.dest_hash, name: h.name || "" });
            }
        }
        for (const h of hubs) {
            if (h.hub_hash && !seen.has(h.hub_hash)) {
                seen.add(h.hub_hash);
                out.push({ hash: h.hub_hash, name: h.hub_name || h.display_name || h.name || "" });
            }
        }
        return out;
    });

    const timelineEntries = $derived.by((): RrcTimelineEntry[] => {
        return buildRelayMessageTimeline(messages, { hideJoinPart }) as unknown as RrcTimelineEntry[];
    });

    const useVirtualMessageList = $derived(
        timelineEntries.length >= MIN_VIRTUAL_RELAY_ENTRIES && GlobalState.config?.message_list_virtualization !== false
    );

    const searchResults = $derived.by(() => {
        return filterRelayMessages(messages, messageSearch, (msg) => displayName(msg));
    });

    const offlineMembers = $derived.by((): RrcMember[] => {
        if (!showMembers) return [];
        const onlineHashes = new Set(members.map((m) => m.hash));
        const seen = new Map<string, RrcMember>();
        for (const msg of messages) {
            if (!msg.src || onlineHashes.has(msg.src) || seen.has(msg.src)) {
                continue;
            }
            seen.set(msg.src, { hash: msg.src, name: msg.nick || msg.src.slice(0, 12) });
        }
        return Array.from(seen.values()).sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
    });

    // --- drafts --------------------------------------------------------------

    function relayDraftKey(hubH: string | null, roomN: string | null): string {
        return `${hubH || ""}/${roomN || ""}`;
    }

    // Identity captured at load/switch time wins over live config so a
    // deferred save cannot write one identity's state into another's
    // localStorage bucket.
    function scopedIdentityKey(): string {
        return identityScope.keyForWrite();
    }

    function saveCurrentRoomDraft() {
        if (!selectedHubHash || !selectedRoom) {
            return;
        }
        saveDraft(relayDraftKey(selectedHubHash, selectedRoom), scopedIdentityKey(), composer);
    }

    function loadRoomDraft(hubH: string, roomN: string) {
        const key = identityScope.beginIdentity();
        composer = loadDraft(relayDraftKey(hubH, roomN), key);
    }

    // --- relay prefs (ignored peers, highlight words, join/part visibility) ---

    function loadRelayPrefsState() {
        const prefs = loadRelayPrefs(scopedIdentityKey());
        ignoredPeers = prefs.ignored;
        highlightWords = prefs.highlightWords;
        hideJoinPart = prefs.hideJoinPart === true;
    }

    function persistRelayPrefs() {
        saveRelayPrefs(scopedIdentityKey(), {
            ignored: ignoredPeers,
            highlightWords,
            hideJoinPart,
        });
    }

    function isHiddenPresenceMessage(msg: RrcMessage): boolean {
        return hideJoinPart && isRelayPeerJoinPartMessage(msg);
    }

    function setHideJoinPart(value: boolean) {
        hideJoinPart = value === true;
        persistRelayPrefs();
    }

    function isOwnRelayMessage(msg: RrcMessage | null | undefined): boolean {
        const own = GlobalState.config?.identity_hash;
        return Boolean(own && typeof msg?.src === "string" && msg.src.toLowerCase() === String(own).toLowerCase());
    }

    function isIgnoredMsg(msg: RrcMessage | null | undefined): boolean {
        return isIgnoredRelayMessage(msg, ignoredPeers, String(GlobalState.config?.identity_hash || ""));
    }

    function isIgnoredAuthor(msg: RrcMessage | null | undefined): boolean {
        if (!msg) return false;
        return ignoredPeers.some((entry) => relayPrefsEqualIgnored(entry, msg));
    }

    function canIgnoreMessageAuthor(msg: RrcMessage | null | undefined): boolean {
        if (!msg || (msg.kind !== "msg" && msg.kind !== "action")) {
            return false;
        }
        if (isOwnRelayMessage(msg)) {
            return false;
        }
        return Boolean((typeof msg.src === "string" && msg.src.trim()) || displayName(msg));
    }

    function purgeIgnoredMessages() {
        const kept = messages.filter((m) => !isIgnoredMsg(m));
        if (kept.length !== messages.length) {
            messages = kept;
        }
    }

    async function toggleIgnoreFromMenu() {
        const msg = messageMenu.msg;
        closeMessageMenu();
        if (!canIgnoreMessageAuthor(msg)) {
            return;
        }
        const name = displayName(msg);
        if (isIgnoredAuthor(msg)) {
            await removeIgnoredPeerForMessage(msg!);
            return;
        }
        const entry = {
            hash: typeof msg!.src === "string" ? msg!.src.trim().toLowerCase() : "",
            name: typeof msg!.nick === "string" && msg!.nick.trim() ? msg!.nick.trim() : name,
        };
        const dupe = ignoredPeers.some(
            (p) =>
                (entry.hash && p.hash === entry.hash) ||
                (entry.name && p.name.toLowerCase() === entry.name.toLowerCase())
        );
        if (!dupe) {
            ignoredPeers = [...ignoredPeers, entry];
            persistRelayPrefs();
        }
        purgeIgnoredMessages();
        ToastUtils.info(t("relay_chat.ignore_added", { name }));
    }

    async function removeIgnoredPeerForMessage(msg: RrcMessage) {
        const name = displayName(msg);
        ignoredPeers = ignoredPeers.filter((p) => !relayPrefsEqualIgnored(p, msg));
        persistRelayPrefs();
        ToastUtils.info(t("relay_chat.ignore_removed", { name }));
        await softResyncOpenRoom();
    }

    async function removeIgnoredPeer(peer: RrcIgnoredPeer) {
        ignoredPeers = ignoredPeers.filter((p) => p !== peer);
        persistRelayPrefs();
        await softResyncOpenRoom();
    }

    function openChatPrefs() {
        showChatPrefs = true;
    }

    function addHighlightWord(word: string) {
        const normalized = normalizeHighlightWordInput(word);
        if (!normalized) {
            return false;
        }
        const exists = highlightWords.some((w) => w.toLowerCase() === normalized.toLowerCase());
        if (!exists) {
            highlightWords = [...highlightWords, normalized];
            persistRelayPrefs();
            refreshHighlightFlags();
        }
        return true;
    }

    function removeHighlightWord(word: string) {
        highlightWords = highlightWords.filter((w) => w !== word);
        persistRelayPrefs();
        refreshHighlightFlags();
    }

    function matchesHighlightWords(text: unknown): boolean {
        return relayTextMatchesWords(text, highlightWords);
    }

    function applyLocalHighlightFlags(msgs: RrcMessage[]) {
        if (!highlightWords.length || !Array.isArray(msgs)) {
            return;
        }
        for (const msg of msgs) {
            if (!msg || (msg.kind !== "msg" && msg.kind !== "action") || msg.mention) {
                continue;
            }
            if (isOwnRelayMessage(msg) || isIgnoredMsg(msg)) {
                continue;
            }
            if (matchesHighlightWords(msg.text)) {
                msg.mention = true;
                // Track locally set flags so removing a word can undo them
                // without touching server-side mention flags.
                msg.localMention = true;
            }
        }
    }

    function clearLocalHighlightFlags(msgs: RrcMessage[]) {
        if (!Array.isArray(msgs)) {
            return;
        }
        for (const msg of msgs) {
            if (msg?.localMention) {
                msg.mention = false;
                delete msg.localMention;
            }
        }
    }

    function refreshHighlightFlags() {
        clearLocalHighlightFlags(messages);
        applyLocalHighlightFlags(messages);
    }

    function shouldBumpRoomMention(msg: RrcMessage): boolean {
        if (!msg || (msg.kind !== "msg" && msg.kind !== "action") || msg.mention) {
            return false;
        }
        if (isOwnRelayMessage(msg) || isIgnoredMsg(msg)) {
            return false;
        }
        return matchesHighlightWords(msg.text);
    }

    function flagLocalRoomMention(hubH: string, roomN: string) {
        if (!hubH || !roomN) {
            return;
        }
        const rooms = localMentionRooms[hubH] || [];
        if (!rooms.includes(roomN)) {
            localMentionRooms = { ...localMentionRooms, [hubH]: [...rooms, roomN] };
        }
        applyLocalMentionRooms();
    }

    function applyLocalMentionRooms() {
        // Custom highlight words are client-side, so the server never sets
        // mention_rooms for them. Reapply our local flags after every hub
        // refresh or the next fetchHubs response would silently drop them.
        for (const [hubH, rooms] of Object.entries(localMentionRooms)) {
            const hub = hubs.find((h) => h.hub_hash === hubH);
            if (!hub) {
                continue;
            }
            if (!Array.isArray(hub.mention_rooms)) {
                hub.mention_rooms = [];
            }
            for (const roomN of rooms) {
                if (!hub.mention_rooms.includes(roomN)) {
                    hub.mention_rooms = [...hub.mention_rooms, roomN];
                }
            }
        }
        updateUnreadBadge();
    }

    function clearLocalRoomMentionFlag(hubH: string, roomN: string) {
        const rooms = localMentionRooms[hubH];
        if (!rooms) {
            return;
        }
        const next = rooms.filter((r) => r !== roomN);
        const copy = { ...localMentionRooms };
        if (next.length === 0) {
            delete copy[hubH];
        } else {
            copy[hubH] = next;
        }
        localMentionRooms = copy;
    }

    // --- lifecycle ----------------------------------------------------------

    function onIdentitySwitched(json?: { identity_hash?: string }) {
        // Invalidate in-flight selectRoom/softResync work first so a stale
        // response cannot merge old-identity messages, POST a read receipt
        // as the new identity, or overwrite the saved layout.
        roomSelectSequence += 1;
        saveCurrentRoomDraft();
        identityScope.beginIdentity(
            typeof json?.identity_hash === "string" && json.identity_hash ? json.identity_hash : undefined
        );
        hubs = [];
        serverHubs = [];
        discovered = [];
        messages = [];
        members = [];
        selectedHubHash = null;
        selectedRoom = null;
        viewBeforeRoomOpen = null;
        messageTranslations = {};
        composer = "";
        nickCycle = null;
        relayAtBottom = true;
        newMessagesBelow = 0;
        localMentionRooms = {};
        loadRelayPrefsState();
        expandedHubs = {};
        availableRoomsExpanded = {};
        availableRoomsRefreshing = {};
        GlobalState.relayChatUnreadCount = 0;
        fetchHubs();
        fetchServers();
        if (!isPopoutMode) {
            fetchDiscovered();
        }
    }

    async function onWebsocketReconnected() {
        await fetchHubs();
        await fetchServers();
        if (!isPopoutMode) {
            await fetchDiscovered();
        }
        if (selectedHubHash && selectedRoom) {
            await softResyncOpenRoom();
        }
    }

    async function softResyncOpenRoom() {
        const hubH = selectedHubHash;
        const roomN = selectedRoom;
        if (!hubH || !roomN) {
            return;
        }
        const seq = roomSelectSequence;
        try {
            const response = await window.api.get(
                apiPath(`/rrc/hubs/${hubH}/rooms/${encodeURIComponent(roomN)}/messages`),
                { params: { limit: RELAY_MESSAGES_INITIAL_PAGE_SIZE } }
            );
            if (seq !== roomSelectSequence || hubH !== selectedHubHash || roomN !== selectedRoom) {
                return;
            }
            const loaded = ((response.data?.messages || []) as RrcMessage[]).filter((m) => !isIgnoredMsg(m));
            messages = mergeRelayMessages(loaded, messages) as RrcMessage[];
            applyLocalHighlightFlags(messages);
            if (Array.isArray(response.data?.members)) {
                members = response.data.members;
            } else {
                await refreshMembers();
            }
            if (typeof response.data?.has_more === "boolean") {
                hasMorePrevious = Boolean(response.data.has_more);
            }
            scrollToBottom();
        } catch {
            // best-effort REST catch-up after live gap
        }
    }

    onMount(() => {
        onWsEvent(WS_EVENTS.RRC_CHANGE, onRrcChange);
        onWsEvent(WS_EVENTS.RRC_MESSAGE, onRrcMessage);
        onWsEvent(WS_EVENTS.RRC_SERVER_CHANGE, onRrcServerChange);
        onWsEvent(WS_EVENTS.ANNOUNCE, onAnnounceEvent);
        GlobalEmitter.on(EMITTER_EVENTS.IDENTITY_SWITCHED, onIdentitySwitched);
        GlobalEmitter.on(EMITTER_EVENTS.WEBSOCKET_RECONNECTED, onWebsocketReconnected);
        smMq = window.matchMedia("(min-width: 640px)");
        smUp = smMq.matches;
        smMq.addEventListener("change", onSmMqChange);
        hostUptimeAnchorMs = Date.now();
        hostUptimeTimer = setInterval(() => {
            if (view === "host" && serverHubs.some((h) => h.running)) {
                hostUptimeTick += 1;
            }
        }, 1000);
        fetchHubs().then(() => {
            restoreRelayLayout();
            applyPopoutRoute();
            applyRouteQuery();
        });
        fetchServers();
        if (!isPopoutMode) {
            fetchDiscovered();
        }
        loadTranslationPacks();
        loadRelayPrefsState();
    });

    onDestroy(() => {
        saveCurrentRoomDraft();
        offWsEvent(WS_EVENTS.RRC_CHANGE, onRrcChange);
        offWsEvent(WS_EVENTS.RRC_MESSAGE, onRrcMessage);
        offWsEvent(WS_EVENTS.RRC_SERVER_CHANGE, onRrcServerChange);
        offWsEvent(WS_EVENTS.ANNOUNCE, onAnnounceEvent);
        GlobalEmitter.off(EMITTER_EVENTS.IDENTITY_SWITCHED, onIdentitySwitched);
        GlobalEmitter.off(EMITTER_EVENTS.WEBSOCKET_RECONNECTED, onWebsocketReconnected);
        if (discoverySearchTimer) {
            clearTimeout(discoverySearchTimer);
        }
        if (hostUptimeTimer) {
            clearInterval(hostUptimeTimer);
            hostUptimeTimer = null;
        }
        if (smMq) {
            smMq.removeEventListener("change", onSmMqChange);
        }
        persistRelayLayout();
        // Leaving the page must stop treating the last room as "viewed" so new
        // mentions while away can bump unread again.
        window.api?.post?.(apiPath("/rrc/active/clear")).catch(() => {});
    });

    // --- view + layout persistence ------------------------------------------

    function selectView(next: RelayView) {
        if (next !== "host") {
            closeHostModeration();
        }
        view = next;
        persistRelayLayout();
        if (next === "discovery") {
            fetchDiscovered();
        } else if (next === "host") {
            fetchServers();
        }
    }

    function persistRelayLayout() {
        if (isPopoutMode) {
            return;
        }
        saveRelayLayout({
            view,
            selectedHubHash,
            selectedRoom,
            expandedHubs: { ...expandedHubs },
            availableRoomsExpanded: { ...availableRoomsExpanded },
            relaySidebarCollapsed,
        });
    }

    function restoreRelayLayout() {
        if (isPopoutMode) {
            return;
        }
        const saved = loadRelayLayout() as Record<string, any> | null;
        if (!saved) {
            return;
        }
        if (["chat", "discovery", "host", "bots", "search"].includes(saved.view)) {
            view = saved.view;
        }
        if (typeof saved.relaySidebarCollapsed === "boolean") {
            relaySidebarCollapsed = saved.relaySidebarCollapsed;
        }
        if (saved.expandedHubs && typeof saved.expandedHubs === "object") {
            expandedHubs = { ...saved.expandedHubs };
        }
        if (saved.availableRoomsExpanded && typeof saved.availableRoomsExpanded === "object") {
            availableRoomsExpanded = { ...saved.availableRoomsExpanded };
        }
        // Older layouts stored the room under selectedRoomName.
        const savedRoom = saved.selectedRoom ?? saved.selectedRoomName ?? null;
        if (saved.selectedHubHash && hubs.some((h) => h.hub_hash === saved.selectedHubHash)) {
            selectedHubHash = saved.selectedHubHash;
            expandedHubs[saved.selectedHubHash] = true;
            const hub = hubs.find((h) => h.hub_hash === saved.selectedHubHash);
            const rooms = hub ? orderedRoomsFor(hub) : [];
            if (savedRoom && rooms.includes(savedRoom)) {
                selectRoom(saved.selectedHubHash, savedRoom);
            } else if (rooms.length > 0) {
                selectRoom(saved.selectedHubHash, rooms[0]);
            }
        }
    }

    function onSmMqChange() {
        smUp = smMq?.matches ?? false;
    }

    function toggleSidebarCollapsed() {
        relaySidebarCollapsed = !relaySidebarCollapsed;
        saveFeatureSidebarCollapsed("relayChat", relaySidebarCollapsed);
        persistRelayLayout();
    }

    // --- sidebar --------------------------------------------------------------

    function orderedRoomsFor(hub: RrcHub | null): string[] {
        return orderedKnownRoomNames(hub);
    }

    function availableRoomsFor(hub: RrcHub | null): RrcAvailableRoom[] {
        return unjoinedAvailableRooms(hub?.available_rooms, orderedRoomsFor(hub), hub?.available_keyed_rooms);
    }

    function onCollapsedHubClick(hub: RrcHub) {
        const rooms = orderedRoomsFor(hub);
        selectedHubHash = hub.hub_hash;
        expandedHubs[hub.hub_hash] = true;
        if (rooms.length > 0) {
            selectRoom(hub.hub_hash, rooms[0]);
        }
    }

    function toggleHub(hubH: string) {
        selectedHubHash = hubH;
        expandedHubs[hubH] = !expandedHubs[hubH];
        persistRelayLayout();
    }

    function isAvailableRoomsExpanded(hubH: string): boolean {
        return availableRoomsExpanded[hubH] !== false;
    }

    function toggleAvailableRooms(hubH: string) {
        availableRoomsExpanded[hubH] = !isAvailableRoomsExpanded(hubH);
        persistRelayLayout();
    }

    function isRefreshingAvailableRooms(hubH: string): boolean {
        return !!availableRoomsRefreshing[hubH];
    }

    async function refreshAvailableRooms(hub: RrcHub) {
        if (!hub?.hub_hash || !isHubConnected(hub) || isRefreshingAvailableRooms(hub.hub_hash)) {
            return;
        }
        availableRoomsRefreshing = { ...availableRoomsRefreshing, [hub.hub_hash]: true };
        try {
            await window.api.post(apiPath(`/rrc/hubs/${hub.hub_hash}/rooms/list`));
            ToastUtils.info(t("relay_chat.rooms_list_requested"));
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        } finally {
            const next = { ...availableRoomsRefreshing };
            delete next[hub.hub_hash];
            availableRoomsRefreshing = next;
        }
    }

    async function onReorderHubs(fromIdx: number, toIdx: number) {
        if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0 || fromIdx >= hubs.length || toIdx >= hubs.length) {
            return;
        }
        const next = [...hubs];
        const [moved] = next.splice(fromIdx, 1);
        next.splice(toIdx, 0, moved);
        hubs = next;
        try {
            await window.api.put(apiPath("/rrc/hubs/order"), {
                hub_hashes: hubs.map((h) => h.hub_hash),
            });
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
            await fetchHubs();
        }
    }

    function onReorderRooms(hub: RrcHub, fromIdx: number, toIdx: number) {
        if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0) {
            return;
        }
        const current = hubs.find((h) => h.hub_hash === hub.hub_hash);
        if (!current) {
            return;
        }
        const rooms = orderedRoomsFor(current);
        if (fromIdx >= rooms.length || toIdx >= rooms.length) {
            return;
        }
        const nextRooms = [...rooms];
        const [moved] = nextRooms.splice(fromIdx, 1);
        nextRooms.splice(toIdx, 0, moved);
        current.known_rooms = nextRooms;
    }

    async function onPersistRoomOrder(hub: RrcHub) {
        const current = hubs.find((h) => h.hub_hash === hub.hub_hash) || hub;
        try {
            await window.api.put(apiPath(`/rrc/hubs/${current.hub_hash}/rooms/order`), {
                room_names: orderedRoomsFor(current),
            });
            await fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
            await fetchHubs();
        }
    }

    // --- context menus ---------------------------------------------------------

    function openSidebarContextMenu(event: MouseEvent, ctx: { hub?: RrcHub | null; room?: string | null }) {
        sidebarMenu = {
            show: true,
            x: event.clientX,
            y: event.clientY,
            hub: ctx.hub || null,
            room: ctx.room || null,
        };
        closeMessageMenu();
    }

    function closeSidebarMenu() {
        sidebarMenu.show = false;
    }

    function openMessageContextMenu(event: MouseEvent, msg: RrcMessage) {
        if (!msg || msg.kind === "system" || msg.kind === "notice" || msg.kind === "error") {
            return;
        }
        if (event && preferNativeTextSelectionMenu(event)) {
            return;
        }
        event?.preventDefault?.();
        messageMenu = { show: true, x: event.clientX, y: event.clientY, msg };
        closeSidebarMenu();
    }

    function closeMessageMenu() {
        messageMenu.show = false;
    }

    function openAddHubFromMenu() {
        closeSidebarMenu();
        openAddHub();
    }

    function focusJoinRoomFromMenu() {
        const hub = sidebarMenu.hub;
        closeSidebarMenu();
        if (!hub) {
            return;
        }
        selectedHubHash = hub.hub_hash;
        expandedHubs[hub.hub_hash] = true;
        tick().then(() => {
            const inputs = document.querySelectorAll<HTMLInputElement>("input[data-relay-join-input]");
            inputs[inputs.length - 1]?.focus();
        });
    }

    function connectHubFromMenu() {
        const hub = sidebarMenu.hub;
        closeSidebarMenu();
        if (hub) {
            connectHub(hub);
        }
    }

    function disconnectHubFromMenu() {
        const hub = sidebarMenu.hub;
        closeSidebarMenu();
        if (hub) {
            disconnectHub(hub);
        }
    }

    function openSettingsFromMenu() {
        const hub = sidebarMenu.hub;
        closeSidebarMenu();
        if (hub) {
            openSettings(hub);
        }
    }

    function copyHubAddressFromMenu() {
        const hub = sidebarMenu.hub;
        closeSidebarMenu();
        if (hub?.hub_hash) {
            copyHash(hub.hub_hash);
        }
    }

    function shareHubFromMenu() {
        const hub = sidebarMenu.hub;
        const roomN = sidebarMenu.room;
        closeSidebarMenu();
        if (!hub) {
            return;
        }
        shareHubLink({
            hub_hash: hub.hub_hash,
            name: hubDisplayName(hub),
            room: roomN || "",
            aspect: hub.dest_name || "",
        });
    }

    async function leaveRoomFromMenu() {
        const hub = sidebarMenu.hub;
        const roomN = sidebarMenu.room;
        closeSidebarMenu();
        if (!hub || !roomN) {
            return;
        }
        if (selectedHubHash === hub.hub_hash && selectedRoom === roomN) {
            await leaveRoom();
            return;
        }
        const confirmed = await DialogUtils.confirmCustom(t("relay_chat.leave_room_confirm", { room: roomN }));
        if (!confirmed) {
            return;
        }
        try {
            await window.api.delete(apiPath(`/rrc/hubs/${hub.hub_hash}/rooms/${encodeURIComponent(roomN)}`));
            ToastUtils.success(t("relay_chat.left_room"));
            await fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    function removeHubFromMenu() {
        const hub = sidebarMenu.hub;
        closeSidebarMenu();
        if (hub) {
            removeHub(hub);
        }
    }

    function canQuoteMessage(msg: RrcMessage | null | undefined): boolean {
        return Boolean(msg && typeof msg.text === "string" && msg.text.trim());
    }

    function canMentionMessageAuthor(msg: RrcMessage | null | undefined): boolean {
        if (!msg || !selectedHub) {
            return false;
        }
        const name = displayName(msg);
        return Boolean(name && msg.kind === "msg");
    }

    function replyWithQuoteFromMenu() {
        const msg = messageMenu.msg;
        closeMessageMenu();
        if (!msg) {
            return;
        }
        const author = displayName(msg);
        const prefix = `> ${author}: ${msg.text}\n\n`;
        const cur = composer || "";
        composer = cur + (cur && !cur.endsWith("\n") ? "\n" : "") + prefix;
        tick().then(() => composerComp?.focus?.());
    }

    function mentionUserFromMenu() {
        const msg = messageMenu.msg;
        closeMessageMenu();
        if (msg) {
            insertMention(displayName(msg));
        }
    }

    async function copyMessageFromMenu() {
        const msg = messageMenu.msg;
        closeMessageMenu();
        if (!msg?.text) {
            return;
        }
        const ok = await copyTextToClipboard(msg.text);
        if (ok) {
            ToastUtils.success(t("common.copied"));
        } else {
            ToastUtils.error(t("common.failed_to_copy"));
        }
    }

    // --- translation -----------------------------------------------------------

    async function loadTranslationPacks() {
        try {
            translationPacks = await TranslationService.listPacks();
        } catch (e) {
            console.error("Failed to load translation packs:", e);
            translationPacks = [];
        }
    }

    function canTranslateRelayMessage(msg: RrcMessage | null | undefined): boolean {
        return translationPacks.length > 0 && Boolean(msg?.text) && msg?.kind === "msg";
    }

    function defaultRelayTranslatePair(): string {
        try {
            const saved = localStorage.getItem(STORAGE_KEYS.TRANSLATE_TARGET_LANG);
            if (saved && translationPacks.some((p) => p.pair === saved)) {
                return saved;
            }
        } catch {
            /* empty */
        }
        return translationPacks[0]?.pair || "";
    }

    async function translateRelayMessageFromMenu() {
        const msg = messageMenu.msg;
        closeMessageMenu();
        if (!msg?.text) {
            return;
        }
        const pair = defaultRelayTranslatePair();
        if (!pair || pair.length < 4) {
            return;
        }
        const key = messageKey(msg);
        messageTranslations[key] = {
            loading: true,
            text: "",
            from: pair.slice(0, 2),
            to: pair.slice(2, 4),
            showOriginal: false,
        };
        try {
            const result = await TranslationService.translate({
                from: pair.slice(0, 2),
                to: pair.slice(2, 4),
                text: msg.text,
            });
            messageTranslations[key] = {
                loading: false,
                text: (result as any)?.target?.text || "",
                from: pair.slice(0, 2),
                to: pair.slice(2, 4),
                showOriginal: false,
            };
        } catch (e) {
            console.error("Relay translation failed:", e);
            delete messageTranslations[key];
            ToastUtils.error(t("messages.translation_failed"));
        }
    }

    function relayMessageTranslation(msg: RrcMessage): RrcMessageTranslation | null {
        return messageTranslations[messageKey(msg)] || null;
    }

    function relayMessageDisplayText(msg: RrcMessage): string {
        const tr = relayMessageTranslation(msg);
        if (tr && tr.text && !tr.showOriginal && !tr.loading) {
            return tr.text;
        }
        return msg.text;
    }

    function toggleRelayMessageOriginal(msg: RrcMessage) {
        const key = messageKey(msg);
        const tr = messageTranslations[key];
        if (tr) {
            tr.showOriginal = !tr.showOriginal;
        }
    }

    // --- moderation ------------------------------------------------------------

    async function sendModerationCommand(template: string, msg: RrcMessage | null) {
        if (!selectedHub || !selectedRoom || !msg) {
            return;
        }
        // Prefer identity hash so spaced/ambiguous nicks cannot mis-target.
        const target =
            typeof msg.src === "string" && /^[a-fA-F0-9]{8,64}$/.test(msg.src.trim())
                ? msg.src.trim().toLowerCase()
                : displayName(msg);
        const roomN = selectedRoom;
        const text = template.replace("{room}", roomN).replace("{target}", target);
        try {
            await window.api.post(apiPath(`/rrc/hubs/${selectedHubHash}/command`), { text, room: roomN });
            ToastUtils.success(t("common.success"));
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    function kickUserFromMenu() {
        const msg = messageMenu.msg;
        closeMessageMenu();
        sendModerationCommand("/kick {room} {target}", msg);
    }

    function banUserFromMenu() {
        const msg = messageMenu.msg;
        closeMessageMenu();
        sendModerationCommand("/ban {room} add {target}", msg);
    }

    // --- composer ---------------------------------------------------------------

    function insertMention(name: string) {
        if (!name) {
            return;
        }
        const mention = "@" + name.replace(/\s/g, "") + " ";
        const cur = composer || "";
        composer = cur + (cur && !cur.endsWith(" ") ? " " : "") + mention;
        tick().then(() => composerComp?.focus?.());
    }

    function onComposerKeydown(event: KeyboardEvent) {
        if (event.key !== "Tab") {
            if (event.key !== "Shift") {
                nickCycle = null;
            }
            return;
        }
        event.preventDefault();
        const el = event.target as HTMLInputElement | HTMLTextAreaElement | null;
        // The caret indexes the DOM value; prefer it so a stale binding cannot
        // complete against a different string than the one the caret points into.
        const text = typeof el?.value === "string" ? el.value : composer;
        const caret = typeof el?.selectionStart === "number" ? el.selectionStart : text.length;
        const names = members.map((m) => m?.name).filter(Boolean) as string[];
        const step = relayNickCompletionStep({
            text,
            caret,
            names,
            cycle: nickCycle as never,
            backwards: event.shiftKey,
        }) as { text: string; caret: number; cycle: Record<string, unknown> } | null;
        if (!step) {
            nickCycle = null;
            return;
        }
        composer = step.text;
        nickCycle = step.cycle;
        tick().then(() => {
            if (el && typeof el.setSelectionRange === "function") {
                el.setSelectionRange(step.caret, step.caret);
            }
        });
    }

    async function sendMessage() {
        const text = composer.trim();
        if (!text || !selectedHub || !selectedRoom) {
            return;
        }
        const isAction = text.startsWith("/me ");
        const payload = isAction ? { text: text.slice(4), action: true } : { text };
        sending = true;
        const sentRoom = selectedRoom;
        const sentHub = selectedHubHash;
        try {
            await window.api.post(
                apiPath(`/rrc/hubs/${selectedHubHash}/rooms/${encodeURIComponent(selectedRoom)}/messages`),
                payload
            );
            composer = "";
            nickCycle = null;
            saveDraft(relayDraftKey(sentHub, sentRoom), scopedIdentityKey(), "");
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.send_failed"));
        } finally {
            sending = false;
        }
    }

    // --- room load, scroll, pagination -------------------------------------------

    function timelineEntryKey(entry: RrcTimelineEntry, index = 0): string {
        if (entry.type === "dateDivider") {
            return `date-${entry.dayKey}-${index}`;
        }
        if (entry.type === "presenceGroup") {
            return `presence-${entry.id}-${index}`;
        }
        const msgKey = messageKey(entry.msg);
        return msgKey ? `${msgKey}-${index}` : `idx-${index}`;
    }

    function messageKey(msg: RrcMessage | null | undefined): string {
        return relayMessageKey(msg);
    }

    function formatDateDividerLabel(dayKey?: string): string {
        if (!dayKey || typeof dayKey !== "string") {
            return "";
        }
        const p = dayKey.split("-").map((x) => parseInt(x, 10));
        if (p.length !== 3 || p.some((n) => Number.isNaN(n))) {
            return dayKey;
        }
        const d = new Date(p[0], p[1] - 1, p[2]);
        if (Number.isNaN(d.getTime())) {
            return dayKey;
        }
        const startOf = (dt: Date) => {
            const x = new Date(dt);
            x.setHours(0, 0, 0, 0);
            return x.getTime();
        };
        const today = new Date();
        if (startOf(d) === startOf(today)) {
            return t("messages.date_divider_today");
        }
        const y = new Date(today);
        y.setDate(y.getDate() - 1);
        if (startOf(d) === startOf(y)) {
            return t("messages.date_divider_yesterday");
        }
        try {
            const loc = typeof navigator !== "undefined" && navigator.language ? navigator.language : "en";
            return new Intl.DateTimeFormat(loc, {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
            }).format(d);
        } catch {
            return dayKey;
        }
    }

    function isPresenceGroupExpanded(id?: string): boolean {
        return !!(id && expandedPresenceGroups[id]);
    }

    function togglePresenceGroup(id?: string) {
        if (id) expandedPresenceGroups[id] = !expandedPresenceGroups[id];
    }

    function formatPresenceGroupSummary(entry: RrcTimelineEntry): string {
        const joined = Number(entry?.joinedCount) || 0;
        const left = Number(entry?.leftCount) || 0;
        const connection = Number(entry?.connectionCount) || 0;
        const parts: string[] = [];
        if (joined > 0) {
            parts.push(t("relay_chat.presence_joined", { count: joined }));
        }
        if (left > 0) {
            parts.push(t("relay_chat.presence_left", { count: left }));
        }
        if (connection > 0) {
            parts.push(t("relay_chat.presence_connection", { count: connection }));
        }
        if (parts.length === 0) {
            return t("relay_chat.presence_events", {
                count: Array.isArray(entry?.messages) ? entry.messages.length : 0,
            });
        }
        return parts.join(" · ");
    }

    function oldestLoadedSeq(): number | null {
        let minSeq: number | null = null;
        for (const msg of messages) {
            if (typeof msg.seq !== "number") {
                continue;
            }
            if (minSeq === null || msg.seq < minSeq) {
                minSeq = msg.seq;
            }
        }
        return minSeq;
    }

    async function loadPreviousMessages() {
        if (isLoadingPrevious || !hasMorePrevious || !selectedHubHash || !selectedRoom) {
            return;
        }
        const beforeSeq = oldestLoadedSeq();
        if (beforeSeq === null) {
            hasMorePrevious = false;
            return;
        }
        const seq = roomSelectSequence;
        const hubH = selectedHubHash;
        const roomN = selectedRoom;
        loadPreviousInFlight += 1;
        isLoadingPrevious = true;
        try {
            const response = await window.api.get(
                apiPath(`/rrc/hubs/${hubH}/rooms/${encodeURIComponent(roomN)}/messages`),
                { params: { limit: RELAY_MESSAGES_PREVIOUS_PAGE_SIZE, before_seq: beforeSeq } }
            );
            if (seq !== roomSelectSequence || hubH !== selectedHubHash || roomN !== selectedRoom) {
                return;
            }
            const older = (response.data?.messages || []) as RrcMessage[];
            hasMorePrevious = Boolean(response.data?.has_more);
            if (older.length === 0) {
                return;
            }
            const uniqueOlder = filterUniqueOlderRelayMessages(older, messages) as RrcMessage[];
            if (uniqueOlder.length === 0) {
                if (older.length > 0) {
                    hasMorePrevious = false;
                }
                return;
            }
            // Locally ignored peers never enter the display list, but the
            // pagination window still tracks their seq numbers so history
            // walks do not stall on a filtered page.
            const visibleOlder = uniqueOlder.filter((m) => !isIgnoredMsg(m) && !isHiddenPresenceMessage(m));
            applyLocalHighlightFlags(visibleOlder);
            const scrollEl = scrollContainerEl;
            const prevScrollHeight = scrollEl ? scrollEl.scrollHeight : 0;
            const prevScrollTop = scrollEl ? scrollEl.scrollTop : 0;
            messages = [...visibleOlder, ...messages];
            // Trim after the anchor is restored: removed tail entries sit below
            // the viewport, so scrollTop stays valid.
            const trimTail = () => {
                if (messages.length > MAX_RELAY_MESSAGES) {
                    messages = messages.slice(0, MAX_RELAY_MESSAGES);
                    tailTrimmed = true;
                }
            };
            if (scrollEl) {
                tick().then(() => {
                    const delta = scrollEl.scrollHeight - prevScrollHeight;
                    scrollEl.scrollTop = prevScrollTop + delta;
                    trimTail();
                });
            } else {
                void tick().then(trimTail);
            }
        } catch {
            // Keep hasMorePrevious: one transient failure must not permanently
            // disable history loading for the open room.
        } finally {
            loadPreviousInFlight = Math.max(0, loadPreviousInFlight - 1);
            isLoadingPrevious = loadPreviousInFlight > 0;
        }
    }

    // Live append path. Dedupes via seq/key and drops the oldest entries past
    // the cap, re-anchoring the scroll position for readers in history.
    function pushLiveMessage(msg: RrcMessage): boolean {
        if (relayMessageAlreadyPresent(messages, msg)) {
            return false;
        }
        messages = [...messages, msg];
        if (messages.length <= MAX_RELAY_MESSAGES || headTrimQueued) {
            return true;
        }
        headTrimQueued = true;
        const scrollEl = scrollContainerEl;
        const trimNow = () => {
            headTrimQueued = false;
            // Compute the drop live: pushes landing in the same tick must not
            // each schedule a splice against a stale length, or a burst
            // removes far more than the overflow.
            const drop = messages.length - MAX_RELAY_MESSAGES;
            if (drop <= 0) {
                return;
            }
            if (!scrollEl) {
                messages = messages.slice(drop);
                return;
            }
            const prevScrollHeight = scrollEl.scrollHeight;
            const prevScrollTop = scrollEl.scrollTop;
            messages = messages.slice(drop);
            tick().then(() => {
                scrollEl.scrollTop = Math.max(0, prevScrollTop - (prevScrollHeight - scrollEl.scrollHeight));
            });
        };
        if (!scrollEl) {
            trimNow();
            return true;
        }
        void tick().then(trimNow);
        return true;
    }

    function onMessagesScroll(event: Event) {
        const el = event.target as HTMLElement | null;
        if (!el) {
            return;
        }
        const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        const near = distanceToBottom <= RELAY_NEAR_BOTTOM_PX;
        relayAtBottom = near;
        if (near) {
            newMessagesBelow = 0;
        }
        if (tailTrimmed && distanceToBottom <= LOAD_PREVIOUS_SCROLL_EDGE_PX && !reloadingLatest) {
            reloadingLatest = true;
            tailTrimmed = false;
            Promise.resolve(selectRoom(selectedHubHash, selectedRoom)).finally(() => {
                reloadingLatest = false;
            });
            return;
        }
        if (isLoadingPrevious || !hasMorePrevious) {
            return;
        }
        if (el.scrollTop <= LOAD_PREVIOUS_SCROLL_EDGE_PX) {
            void loadPreviousMessages();
        }
    }

    function scrollToBottom() {
        relayAtBottom = true;
        newMessagesBelow = 0;
        tick().then(() => {
            if (useVirtualMessageList && virtualListComp) {
                virtualListComp.scrollToBottom?.();
                return;
            }
            const el = scrollContainerEl;
            if (el) {
                el.scrollTop = el.scrollHeight;
            }
        });
    }

    function scrollToMessage(msg: RrcMessage) {
        if (!msg) {
            return;
        }
        showSearch = false;
        const key = messageKey(msg);
        if (useVirtualMessageList) {
            tick().then(() => virtualListComp?.scrollToMessageKey?.(key));
            return;
        }
        tick().then(() => {
            const el = scrollContainerEl?.querySelector(`[data-msg-key="${key}"]`);
            (el as HTMLElement | null)?.scrollIntoView({ block: "center", behavior: "smooth" });
        });
    }

    // --- room selection ---------------------------------------------------------

    export async function openSearchResult(target: { hubHash: string; room: string }) {
        if (!target?.hubHash || !target?.room) {
            return;
        }
        let hubObj = hubs.find((h) => h.hub_hash === target.hubHash);
        if (!hubObj) {
            // The local list may just be stale or still loading; refresh once
            // before deciding the hub is genuinely absent.
            await fetchHubs();
            hubObj = hubs.find((h) => h.hub_hash === target.hubHash);
        }
        if (!hubObj) {
            // The hub is not in the local list (never added or disconnected),
            // so selecting it would leave the pane blank with no feedback.
            ToastUtils.warning(t("relay_chat.hub_not_added"));
            return;
        }
        // Capture before the switch so backing out returns to Search.
        viewBeforeRoomOpen = view;
        view = "chat";
        persistRelayLayout();
        selectRoom(target.hubHash, target.room);
    }

    export function onBackFromRoom() {
        saveCurrentRoomDraft();
        selectedRoom = null;
        composer = "";
        nickCycle = null;
        relayAtBottom = true;
        newMessagesBelow = 0;
        restoreViewAfterRoomClose();
    }

    function restoreViewAfterRoomClose() {
        if (viewBeforeRoomOpen && viewBeforeRoomOpen !== view) {
            view = viewBeforeRoomOpen;
        }
        viewBeforeRoomOpen = null;
    }

    export async function selectRoom(hubOrHash: RrcHub | string | null, roomOrName: RrcRoom | string | null) {
        const hubH = typeof hubOrHash === "string" ? hubOrHash : hubOrHash?.hub_hash || null;
        const roomN = typeof roomOrName === "string" ? roomOrName : roomOrName?.name || null;
        if (!hubH || !roomN) {
            return;
        }
        if (selectedRoom === null && viewBeforeRoomOpen == null) {
            viewBeforeRoomOpen = view;
        }
        saveCurrentRoomDraft();
        selectedHubHash = hubH;
        selectedRoom = roomN;
        expandedHubs[hubH] = true;
        hasMorePrevious = false;
        expandedPresenceGroups = {};
        // Clear before fetch so only websocket arrivals during the request are merged back.
        messages = [];
        members = [];
        nickCycle = null;
        relayAtBottom = true;
        newMessagesBelow = 0;
        loadRoomDraft(hubH, roomN);
        const seq = ++roomSelectSequence;
        try {
            const response = await window.api.get(
                apiPath(`/rrc/hubs/${hubH}/rooms/${encodeURIComponent(roomN)}/messages`),
                { params: { limit: RELAY_MESSAGES_INITIAL_PAGE_SIZE } }
            );
            if (seq !== roomSelectSequence) {
                return;
            }
            const loaded = ((response.data?.messages || []) as RrcMessage[]).filter((m) => !isIgnoredMsg(m));
            messages = mergeRelayMessages(loaded, messages) as RrcMessage[];
            applyLocalHighlightFlags(messages);
            members = response.data?.members || [];
            hasMorePrevious = Boolean(response.data?.has_more);
            scrollToBottom();
            // Always dismiss unread for the opened room (including layout restore /
            // page navigation when the room was already selected).
            await markRoomRead(hubH, roomN, { refreshHubs: true });
            persistRelayLayout();
        } catch {
            if (seq !== roomSelectSequence) {
                return;
            }
            hasMorePrevious = false;
        }
    }

    function clearLocalRoomUnread(hubH: string, roomN: string) {
        clearLocalRoomMentionFlag(hubH, roomN);
        const hub = hubs.find((h) => h.hub_hash === hubH);
        if (!hub) {
            return;
        }
        if (Array.isArray(hub.mention_rooms)) {
            hub.mention_rooms = hub.mention_rooms.filter((r) => r !== roomN);
        }
        if (Array.isArray(hub.unread_rooms)) {
            hub.unread_rooms = hub.unread_rooms.filter((r) => r !== roomN);
        }
        if (hub.unread_counts && typeof hub.unread_counts === "object") {
            const next = { ...hub.unread_counts };
            delete next[roomN];
            hub.unread_counts = next;
        }
        if (typeof hub.total_unread === "number") {
            hub.total_unread = Object.values(hub.unread_counts || {}).reduce((sum, n) => sum + (Number(n) || 0), 0);
        }
        updateUnreadBadge();
    }

    async function markRoomRead(hubH: string, roomN: string, { refreshHubs = false } = {}) {
        if (!hubH || !roomN) {
            return;
        }
        clearLocalRoomUnread(hubH, roomN);
        try {
            await window.api.post(apiPath(`/rrc/hubs/${hubH}/rooms/${encodeURIComponent(roomN)}/read`));
        } catch {
            // GET messages already marks active/read on the server. Ignore duplicate failures.
        }
        if (refreshHubs) {
            await fetchHubs();
            // Keep dismiss sticky if a concurrent hubs fetch still had the old unread.
            clearLocalRoomUnread(hubH, roomN);
        } else {
            updateUnreadBadge();
        }
    }

    async function refreshMembers() {
        const hubH = selectedHubHash;
        const roomN = selectedRoom;
        if (!hubH || !roomN) {
            return;
        }
        try {
            const response = await window.api.get(
                apiPath(`/rrc/hubs/${hubH}/rooms/${encodeURIComponent(roomN)}/messages`)
            );
            // The user may have switched rooms while this was in flight;
            // only the still-selected room may write the sidebar roster.
            if (selectedHubHash !== hubH || selectedRoom !== roomN) {
                return;
            }
            members = response.data?.members || [];
        } catch {
            // ignore member refresh failures
        }
    }

    function updateUnreadBadge() {
        GlobalState.relayChatUnreadCount = countRelayMentions(hubs);
    }

    // --- message html, links ----------------------------------------------------

    function renderMessageHtml(text: string): string {
        return MarkdownRenderer.renderBasic(text || "");
    }

    function handleMessageHtmlClick(event: MouseEvent) {
        const hex32 = /^[a-fA-F0-9]{32}$/;
        const routeName = isPopoutMode ? "nomadnetwork-popout" : "nomadnetwork";
        handleRichHtmlLinkClick(event, {
            scrollRoot: scrollContainerEl,
            onNomadUrl: (url) => {
                const [hash, ...pathParts] = url.split(":");
                const path = pathParts.join(":");
                if (!hex32.test(hash)) {
                    return;
                }
                navigate({ name: routeName, params: { destinationHash: hash }, query: { path } });
            },
            onLxmfAddress: (address) => {
                navigate({ name: "messages", params: { destinationHash: address } });
            },
            onGeo: (geoText) => {
                void openGeoOnMap(geoText);
            },
            onRrcUrl: (uri) => {
                void openRelayRoomLink(uri);
            },
        });
    }

    async function openRelayRoomLink(uri: string) {
        const parsed = parseRelayUri(uri);
        if (!parsed) {
            ToastUtils.error(t("messages.relay_link_invalid"));
            return;
        }
        if (GlobalState.config?.rrc_enabled === false) {
            ToastUtils.warning(t("messages.relay_link_disabled"));
            return;
        }
        try {
            const result = await applyRelayShareLink(parsed);
            await fetchHubs();
            view = "chat";
            expandedHubs[result.hub_hash] = true;
            if (result.room) {
                await selectRoom(result.hub_hash, result.room);
            } else {
                selectedHubHash = result.hub_hash;
            }
            ToastUtils.success(t("messages.relay_link_opened"));
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("messages.relay_link_failed"));
        }
    }

    async function openGeoOnMap(geoText: string) {
        try {
            const { resolveGeoText } = await import("../../../js/geoLinkify.js");
            const point = await resolveGeoText(geoText);
            if (!point) {
                ToastUtils.error(t("map.geo_parse_failed"));
                return;
            }
            navigate({
                name: "map",
                query: {
                    lat: point.lat.toFixed(6),
                    lon: point.lon.toFixed(6),
                    zoom: "12",
                    label: String(geoText).trim(),
                },
            });
        } catch {
            ToastUtils.error(t("map.geo_parse_failed"));
        }
    }

    // --- misc helpers ------------------------------------------------------------

    function formatHash(hash?: string | null): string {
        if (!hash) {
            return "-";
        }
        return Utils.formatDestinationHash(hash);
    }

    function timeAgo(datetime?: string | null): string {
        return Utils.formatTimeAgoForI18n(datetime);
    }

    function copyHash(hash?: string | null) {
        if (!hash) {
            return;
        }
        copyTextToClipboard(hash).then((ok) => {
            if (ok) {
                ToastUtils.success(t("relay_chat.hash_copied"));
            }
        });
    }

    async function copyMemberHash(member: RrcMember) {
        if (!member?.hash) {
            return;
        }
        const ok = await copyTextToClipboard(member.hash);
        if (ok) {
            ToastUtils.success(t("relay_chat.copy_hash"));
        } else {
            ToastUtils.error(t("common.failed_to_copy"));
        }
    }

    async function openMemberDm(member: RrcMember) {
        const hash = member?.hash;
        if (!hash || memberDmLoadingHash) {
            return;
        }
        memberDmLoadingHash = hash;
        try {
            const res = await window.api.get(apiPath(`/identity/${hash}/lxmf-address`));
            const lxmf = res?.data?.lxmf_destination_hash;
            if (!lxmf) {
                throw new Error(t("relay_chat.dm_no_lxmf"));
            }
            if (!res.data.has_path) {
                try {
                    await window.api.post(apiPath(`/destination/${lxmf}/path`));
                } catch {
                    // path request best-effort; the messages page retries on send
                }
            }
            navigate({ name: "messages", params: { destinationHash: lxmf } });
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || e.message || t("relay_chat.dm_failed"));
        } finally {
            memberDmLoadingHash = null;
        }
    }

    async function shareHubLink({
        hub_hash,
        name = "",
        room: roomN = "",
        aspect = "",
    }: { hub_hash?: string; name?: string; room?: string; aspect?: string } = {}) {
        const text = buildRelayShareMessage({
            hub: hub_hash,
            name,
            room: roomN,
            aspect,
        });
        if (!text) {
            ToastUtils.error(t("relay_chat.action_failed"));
            return;
        }
        const ok = await copyTextToClipboard(text);
        if (ok) {
            ToastUtils.success(t("relay_chat.share_copied"));
        } else {
            ToastUtils.error(t("relay_chat.action_failed"));
        }
    }

    // --- hubs ---------------------------------------------------------------------

    async function fetchHubs() {
        try {
            const response = await window.api.get(apiPath("/rrc/hubs"));
            hubs = response.data?.hubs || [];
            if (!selectedHubHash && hubs.length > 0) {
                selectedHubHash = hubs[0].hub_hash;
                expandedHubs[hubs[0].hub_hash] = true;
            }
            applyLocalMentionRooms();
        } catch {
            // relay chat may be unavailable for this identity
        }
    }

    async function joinRoom(hub: RrcHub) {
        const roomN = joinRoomName.trim();
        if (!roomN) {
            ToastUtils.warning(t("relay_chat.room_required"));
            return;
        }
        const key = joinRoomKey.trim() || null;
        const joined = await joinRoomByName(hub, roomN, { key });
        if (joined) {
            joinRoomName = "";
            joinRoomKey = "";
        }
    }

    async function joinAvailableRoom(hub: RrcHub, roomN: string) {
        const roomName = String(roomN || "").trim();
        if (!hub || !roomName) {
            return;
        }
        const stored = Array.isArray(hub.stored_key_rooms) && hub.stored_key_rooms.includes(roomName);
        const keyed = Array.isArray(hub.available_keyed_rooms) && hub.available_keyed_rooms.includes(roomName);
        if (stored || !keyed) {
            await joinRoomByName(hub, roomName);
            return;
        }
        const entered = await DialogUtils.prompt(t("relay_chat.room_key_prompt", { room: roomName }), "", {
            inputType: "password",
        });
        if (entered == null) {
            return;
        }
        const key = String(entered).trim();
        if (!key) {
            ToastUtils.warning(t("relay_chat.host_room_key_required"));
            return;
        }
        await joinRoomByName(hub, roomName, { key });
    }

    function isBadKeyErrorText(text: unknown): boolean {
        if (typeof text !== "string") {
            return false;
        }
        const lowered = text.trim().toLowerCase();
        // Match backend: require "bad key" so mode hints like "enable +k" do not wipe storage.
        return lowered.includes("bad key (+k)") || lowered.includes("bad key");
    }

    async function promptForRoomKey(roomN: string): Promise<string | null> {
        const entered = await DialogUtils.prompt(t("relay_chat.room_key_prompt", { room: roomN || "" }), "", {
            inputType: "password",
        });
        if (entered == null) {
            return null;
        }
        const key = String(entered).trim();
        return key || null;
    }

    async function handleBadKeyError(hubH: string, roomN: string | undefined, messageText: string) {
        const roomName = (roomN || "").trim().toLowerCase();
        if (!hubH || !roomName) {
            ToastUtils.error(messageText || t("relay_chat.bad_key"));
            return;
        }
        const flightKey = `${hubH}:${roomName}`;
        if (badKeyPromptInFlight === flightKey) {
            return;
        }
        badKeyPromptInFlight = flightKey;
        try {
            ToastUtils.warning(t("relay_chat.bad_key"));
            const hub = hubs.find((h) => h.hub_hash === hubH);
            if (!hub) {
                return;
            }
            try {
                await window.api.delete(apiPath(`/rrc/hubs/${hubH}/rooms/${encodeURIComponent(roomName)}/key`));
            } catch {
                // Stored key may already be gone after the hub ERROR path.
            }
            const key = await promptForRoomKey(roomName);
            if (!key) {
                return;
            }
            await joinRoomByName(hub, roomName, { key, prompted: true });
        } finally {
            if (badKeyPromptInFlight === flightKey) {
                badKeyPromptInFlight = null;
            }
        }
    }

    async function joinRoomByName(
        hub: RrcHub,
        roomN: string,
        { key = null, prompted = false }: { key?: string | null; prompted?: boolean } = {}
    ): Promise<boolean> {
        try {
            const payload: Record<string, unknown> = { room: roomN, remember: true };
            if (key) {
                payload.key = key;
            }
            await window.api.post(apiPath(`/rrc/hubs/${hub.hub_hash}/rooms`), payload);
            if (isHubConnected(hub)) {
                ToastUtils.info(t("relay_chat.join_requested"));
            } else {
                ToastUtils.success(t("relay_chat.joined_room"));
            }
            await fetchHubs();
            return true;
        } catch (e: any) {
            const message = e?.response?.data?.message || t("relay_chat.action_failed");
            if (!prompted && isBadKeyErrorText(message)) {
                await handleBadKeyError(hub.hub_hash, roomN, message);
                return false;
            }
            ToastUtils.error(message);
            return false;
        }
    }

    async function leaveRoom() {
        if (!selectedHub || !selectedRoom) {
            return;
        }
        const confirmed = await DialogUtils.confirmCustom(t("relay_chat.leave_room_confirm"));
        if (!confirmed) {
            return;
        }
        const roomN = selectedRoom;
        const draftHub = selectedHubHash;
        try {
            await window.api.delete(apiPath(`/rrc/hubs/${selectedHubHash}/rooms/${encodeURIComponent(roomN)}`));
            // A left room is gone for good, so its draft goes with it.
            composer = "";
            saveDraft(relayDraftKey(draftHub, roomN), scopedIdentityKey(), "");
            selectedRoom = null;
            restoreViewAfterRoomClose();
            messages = [];
            members = [];
            ToastUtils.success(t("relay_chat.left_room"));
            await fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function clearMessages() {
        if (!selectedHub || !selectedRoom) {
            return;
        }
        const confirmed = await DialogUtils.confirm(t("relay_chat.clear_messages_confirm"));
        if (!confirmed) {
            return;
        }
        try {
            await window.api.delete(
                apiPath(`/rrc/hubs/${selectedHubHash}/rooms/${encodeURIComponent(selectedRoom)}/messages`)
            );
            messages = [];
            ToastUtils.success(t("relay_chat.messages_cleared"));
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function connectHub(hub: RrcHub) {
        try {
            await window.api.post(apiPath(`/rrc/hubs/${hub.hub_hash}/connect`));
            await fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function disconnectHub(hub: RrcHub) {
        try {
            await window.api.post(apiPath(`/rrc/hubs/${hub.hub_hash}/disconnect`));
            await fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    function openAddHub() {
        showAddHub = true;
    }

    async function handleAddHubSubmit(payload: { hub_hash: string; name?: string; dest_name?: string }) {
        const hubH = payload.hub_hash.trim();
        if (!hubH) {
            ToastUtils.warning(t("relay_chat.invalid_hub_hash"));
            return;
        }
        try {
            const response = await window.api.post(apiPath("/rrc/hubs"), {
                hub_hash: hubH,
                name: payload.name?.trim() || undefined,
                dest_name: payload.dest_name?.trim() || undefined,
                connect: true,
            });
            showAddHub = false;
            ToastUtils.success(t("relay_chat.hub_added"));
            await fetchHubs();
            const added = response.data?.hub;
            if (added) {
                selectedHubHash = added.hub_hash;
                expandedHubs[added.hub_hash] = true;
            }
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.invalid_hub_hash"));
        }
    }

    async function removeHub(hub: RrcHub) {
        const confirmed = await DialogUtils.confirm(t("relay_chat.remove_hub_confirm"));
        if (!confirmed) {
            return;
        }
        try {
            await window.api.delete(apiPath(`/rrc/hubs/${hub.hub_hash}`));
            if (selectedHubHash === hub.hub_hash) {
                selectedHubHash = null;
                selectedRoom = null;
                messages = [];
                members = [];
            }
            ToastUtils.success(t("relay_chat.hub_removed"));
            await fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    function openSettings(hub: RrcHub) {
        settingsHubHash = hub.hub_hash;
        showHubSettings = true;
    }

    async function saveHubSettings(payload: Record<string, unknown>) {
        if (!settingsHubHash) {
            return;
        }
        try {
            await window.api.patch(apiPath(`/rrc/hubs/${settingsHubHash}`), payload);
            showHubSettings = false;
            ToastUtils.success(t("relay_chat.settings_saved"));
            await fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function applyOptionsToAllHubs(options: Record<string, boolean>) {
        if (applyingOptionsToAllHubs) {
            return;
        }
        applyingOptionsToAllHubs = true;
        try {
            await window.api.post(apiPath("/rrc/hubs/options"), options);
            ToastUtils.success(t("relay_chat.auto_options_applied_all_hubs"));
            await fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        } finally {
            applyingOptionsToAllHubs = false;
        }
    }

    function popoutChannel() {
        if (!selectedHubHash || !selectedRoom) {
            return;
        }
        const hub = encodeURIComponent(selectedHubHash);
        const roomPath = encodeURIComponent(selectedRoom);
        const url = `${window.location.origin}${window.location.pathname}#/popout/relay-chat/${hub}/${roomPath}`;
        window.open(url, "_blank", "width=900,height=700,noopener");
    }

    function applyPopoutRoute() {
        const route = getCurrentRoute();
        const hubH = hubHash || (route?.params?.hubHash as string | undefined);
        const routeRoom = room || (route?.params?.room as string | undefined);
        if (!hubH) {
            return;
        }
        view = "chat";
        selectedHubHash = decodeURIComponent(hubH);
        expandedHubs[selectedHubHash] = true;
        if (routeRoom) {
            selectRoom(selectedHubHash, decodeURIComponent(routeRoom));
        }
    }

    function applyRouteQuery() {
        const query = routeQuery || (getCurrentRoute()?.query as Record<string, string> | undefined) || {};
        const hubH = query?.hub;
        const routeRoom = query?.room;
        if (!hubH || typeof hubH !== "string") {
            return;
        }
        view = "chat";
        selectedHubHash = hubH;
        expandedHubs[hubH] = true;
        if (routeRoom && typeof routeRoom === "string") {
            selectRoom(hubH, routeRoom);
        }
    }

    // --- discovery -----------------------------------------------------------------

    function isHubAdded(destinationHash?: string | null): boolean {
        return hubs.some((hub) => hub.hub_hash === destinationHash);
    }

    function nodeName(node: RrcDiscoveredHub): string {
        if (node.custom_display_name) {
            return node.custom_display_name;
        }
        if (node.display_name && node.display_name !== "Anonymous Peer") {
            return node.display_name;
        }
        return formatHash(node.destination_hash);
    }

    async function fetchDiscovered() {
        try {
            const response = await window.api.get(apiPath("/announces"), {
                params: {
                    aspect: RRC_HUB_ASPECT,
                    limit: 200,
                    search: discoverySearch || undefined,
                },
            });
            discovered = response.data?.announces || [];
        } catch {
            discovered = [];
        }
    }

    async function refreshDiscovered() {
        discoveryLoading = true;
        try {
            await fetchDiscovered();
            ToastUtils.info(t("relay_chat.discovery_refreshed") + " (" + discovered.length + ")");
        } finally {
            discoveryLoading = false;
        }
    }

    function onDiscoverySearch() {
        if (discoverySearchTimer) {
            clearTimeout(discoverySearchTimer);
        }
        discoverySearchTimer = setTimeout(() => {
            fetchDiscovered();
        }, 300);
    }

    function upsertDiscovered(announce: RrcDiscoveredHub) {
        const index = discovered.findIndex((n) => n.destination_hash === announce.destination_hash);
        if (index >= 0) {
            discovered.splice(index, 1, announce);
        } else {
            discovered.unshift(announce);
        }
        discovered = [...discovered];
    }

    async function addFromDiscovery(node: RrcDiscoveredHub) {
        try {
            const response = await window.api.post(apiPath("/rrc/hubs"), {
                hub_hash: node.destination_hash,
                name: nodeName(node),
                dest_name: RRC_HUB_ASPECT,
                connect: true,
            });
            ToastUtils.success(t("relay_chat.discovery_added"));
            await fetchHubs();
            const added = response.data?.hub;
            if (added) {
                selectedHubHash = added.hub_hash;
                expandedHubs[added.hub_hash] = true;
            }
            view = "chat";
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    function openDiscovered(node: RrcDiscoveredHub) {
        selectedHubHash = node.destination_hash;
        expandedHubs[node.destination_hash] = true;
        view = "chat";
    }

    // --- hosting ---------------------------------------------------------------------

    function hostedHubUptimeSeconds(hub: RrcHostedHub): number {
        void hostUptimeTick;
        if (!hub?.running) {
            return 0;
        }
        const base = Number(hub.uptime_seconds);
        if (!Number.isFinite(base) || base < 0) {
            return 0;
        }
        if (!hostUptimeAnchorMs) {
            return Math.floor(base);
        }
        return Math.floor(base + (Date.now() - hostUptimeAnchorMs) / 1000);
    }

    async function fetchServers() {
        try {
            const response = await window.api.get(apiPath("/rrc/servers"));
            serverHubs = response.data?.hubs || [];
            hostUptimeAnchorMs = Date.now();
            hostUptimeTick = 0;
        } catch {
            // relay chat hosting may be unavailable for this identity
        }
    }

    async function createServerHub(payload: {
        name: string;
        greeting: string;
        announce: boolean;
        announce_interval_seconds: number;
    }) {
        try {
            await window.api.post(apiPath("/rrc/servers"), {
                name: payload.name.trim() || undefined,
                greeting: payload.greeting.trim() || undefined,
                announce: payload.announce,
                announce_interval_seconds: payload.announce_interval_seconds,
            });
            showCreateHub = false;
            ToastUtils.success(t("relay_chat.host_hub_created"));
            await fetchServers();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function saveHostHubSettings(payload: {
        name: string;
        announce: boolean;
        announce_interval_seconds: number;
    }) {
        if (!hostHubSettingsId) {
            return;
        }
        try {
            await window.api.patch(apiPath(`/rrc/servers/${hostHubSettingsId}`), {
                name: payload.name.trim() || undefined,
                announce: payload.announce,
                announce_interval_seconds: payload.announce_interval_seconds,
            });
            showHostHubSettings = false;
            ToastUtils.success(t("relay_chat.settings_saved"));
            await fetchServers();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    function openHostHubSettings(hub: RrcHostedHub) {
        hostHubSettingsId = hub.id;
        showHostHubSettings = true;
    }

    async function deleteServerHub(hub: RrcHostedHub) {
        const confirmed = await DialogUtils.confirm(t("relay_chat.host_delete_hub_confirm"));
        if (!confirmed) {
            return;
        }
        try {
            await window.api.delete(apiPath(`/rrc/servers/${hub.id}`));
            ToastUtils.success(t("relay_chat.host_hub_deleted"));
            await fetchServers();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function startServerHub(hub: RrcHostedHub) {
        try {
            await window.api.post(apiPath(`/rrc/servers/${hub.id}/start`));
            await fetchServers();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function stopServerHub(hub: RrcHostedHub) {
        try {
            await window.api.post(apiPath(`/rrc/servers/${hub.id}/stop`));
            await fetchServers();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function announceServerHub(hub: RrcHostedHub) {
        try {
            await window.api.post(apiPath(`/rrc/servers/${hub.id}/announce`));
            ToastUtils.success(t("relay_chat.host_announced"));
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    function openHostModeration(
        hub: RrcHostedHub,
        { tab = "rooms", room: roomN = null }: { tab?: string; room?: string | null } = {}
    ) {
        if (!hub) {
            return;
        }
        if (tab === "members" && !hub.running) {
            ToastUtils.warning(t("relay_chat.host_hub_not_running"));
            return;
        }
        hostModeration = {
            hub,
            tab: tab === "members" ? "members" : "rooms",
            room: roomN || null,
        };
    }

    function closeHostModeration() {
        hostModeration = { hub: null, tab: "rooms", room: null };
    }

    async function joinHostedAsClient(hub: RrcHostedHub) {
        if (!hub?.dest_hash) {
            return;
        }
        try {
            const response = await window.api.post(apiPath("/rrc/hubs"), {
                hub_hash: hub.dest_hash,
                name: hub.name || undefined,
                dest_name: RRC_HUB_ASPECT,
                connect: true,
            });
            ToastUtils.success(t("relay_chat.host_joined_as_client"));
            await fetchHubs();
            const added = response.data?.hub;
            if (added) {
                selectedHubHash = added.hub_hash;
                expandedHubs[added.hub_hash] = true;
            } else {
                selectedHubHash = hub.dest_hash;
                expandedHubs[hub.dest_hash] = true;
            }
            view = "chat";
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function leaveHostedAsClient(hub: RrcHostedHub) {
        if (!hub?.dest_hash) {
            return;
        }
        const clientHub = hubs.find((h) => h.hub_hash === hub.dest_hash);
        if (!clientHub) {
            return;
        }
        await removeHub(clientHub);
    }

    // --- websocket events --------------------------------------------------------------

    function onRrcChange() {
        fetchHubs();
    }

    function onRrcMessage(json: any) {
        if (json.message && json.message.kind === "error" && isBadKeyErrorText(json.message.text)) {
            void handleBadKeyError(json.hub_hash, json.room || json.message.room, json.message.text);
        }
        if (json.hub_hash === selectedHubHash && json.room === selectedRoom && json.message) {
            const ignored = isIgnoredMsg(json.message);
            if (!ignored && highlightWords.length) {
                applyLocalHighlightFlags([json.message]);
            }
            if (!ignored && pushLiveMessage(json.message)) {
                if (relayAtBottom) {
                    scrollToBottom();
                } else if (json.message.kind === "msg" || json.message.kind === "action") {
                    newMessagesBelow += 1;
                }
            }
            if (json.message.kind === "system" || json.message.kind === "notice") {
                refreshMembers();
            }
            // Chat is already open: dismiss unread/mention badge without waiting
            // for a later hub list refresh race.
            void markRoomRead(json.hub_hash, json.room);
        } else if (json.message && (json.message.kind === "msg" || json.message.kind === "action")) {
            const ignored = isIgnoredMsg(json.message);
            const bump = !ignored && shouldBumpRoomMention(json.message);
            if (!ignored) {
                const routeName = getCurrentRoute()?.name;
                const onRelayPage = routeName === "relay-chat" || routeName === "relay-chat-popout";
                if (!onRelayPage || json.hub_hash !== selectedHubHash || json.room !== selectedRoom) {
                    ToastUtils.info(t("relay_chat.new_message_toast", { room: json.room || "" }));
                }
            }
            fetchHubs().then(() => {
                if (bump) {
                    flagLocalRoomMention(json.hub_hash, json.room);
                }
            });
        } else {
            fetchHubs();
        }
    }

    function onRrcServerChange() {
        fetchServers();
    }

    function onAnnounceEvent(json: any) {
        if (json.announce && json.announce.aspect === RRC_HUB_ASPECT) {
            upsertDiscovered(json.announce);
        }
    }
</script>

<svelte:window onkeydown={handleOverflowKeydown} />

<div class="flex flex-col flex-1 min-w-0 h-full bg-sem-canvas text-sem-fg">
    {#if !rrcEnabled}
        <div class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center text-sem-fg-muted">
            <MaterialDesignIcon iconName="forum-off-outline" class="size-12 opacity-40" />
            <p class="max-w-md text-sm">{t("relay_chat.disabled_message")}</p>
        </div>
    {:else}
        {#if !isPopoutMode}
            <div
                class="flex items-stretch h-9 shrink-0 border-b border-sem-border bg-sem-surface-muted overflow-x-auto"
                role="tablist"
            >
                {#each tabs as tabItem (tabItem.id)}
                    <button
                        type="button"
                        role="tab"
                        aria-selected={view === tabItem.id}
                        class="inline-flex items-center gap-1.5 px-3 sm:px-4 border-r border-sem-border text-xs sm:text-sm transition-colors shrink-0 cursor-pointer {view ===
                        tabItem.id
                            ? 'bg-sem-canvas text-sem-fg font-semibold'
                            : 'text-sem-fg-muted hover:bg-sem-surface/80'} {OVERFLOW_TAB_IDS.has(tabItem.id)
                            ? 'hidden md:inline-flex'
                            : ''}"
                        onclick={() => selectView(tabItem.id)}
                    >
                        <MaterialDesignIcon iconName={tabItem.icon} class="size-4 shrink-0 opacity-70" />
                        <span>{t(tabItem.label)}</span>
                    </button>
                {/each}

                <!-- mobile overflow: host, bots and search move here so the bar never scrolls -->
                {#if overflowTabs.length > 0}
                    <div class="relative md:hidden shrink-0" bind:this={overflowMenuEl}>
                        <button
                            type="button"
                            role="tab"
                            aria-selected={isOverflowView}
                            aria-label={t("messages.more_actions")}
                            title={t("messages.more_actions")}
                            class="inline-flex h-full items-center gap-1.5 px-3 border-r border-sem-border text-xs transition-colors {isOverflowView
                                ? 'bg-sem-canvas text-sem-fg font-semibold'
                                : 'text-sem-fg-muted hover:bg-sem-surface/80'}"
                            onclick={() => {
                                overflowMenuOpen = !overflowMenuOpen;
                            }}
                        >
                            <MaterialDesignIcon iconName={overflowViewIcon} class="size-4 shrink-0 opacity-70" />
                            {#if overflowViewTab}
                                <span>{t(overflowViewTab.label)}</span>
                            {/if}
                        </button>
                        {#if overflowMenuOpen}
                            <div class="absolute right-0 top-full mt-1 z-50 min-w-44">
                                <div
                                    class="dropdown-caret pointer-events-none absolute -top-[4px] right-3 border-t border-l border-sem-border"
                                    aria-hidden="true"
                                ></div>
                                <div
                                    class="bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg"
                                >
                                    {#each overflowTabs as tabItem (tabItem.id)}
                                        <button
                                            type="button"
                                            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                                            onclick={() => {
                                                overflowMenuOpen = false;
                                                selectView(tabItem.id);
                                            }}
                                        >
                                            <MaterialDesignIcon iconName={tabItem.icon} class="size-5" />
                                            <span>{t(tabItem.label)}</span>
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/if}

        <div class="flex flex-1 min-w-0 overflow-hidden" class:hidden={view !== "chat"}>
            {#if !isPopoutMode}
                <RelayHubSidebar
                    {hubs}
                    {selectedHubHash}
                    {selectedRoom}
                    collapsed={effectiveSidebarCollapsed}
                    {expandedHubs}
                    {availableRoomsExpanded}
                    {availableRoomsRefreshing}
                    {showUnreadBadges}
                    bind:joinRoomName
                    bind:joinRoomKey
                    onaddhub={openAddHub}
                    ontogglecollapse={toggleSidebarCollapsed}
                    ontogglehub={toggleHub}
                    oncollapsedhubclick={onCollapsedHubClick}
                    onselectroom={(hub, roomN) => selectRoom(hub.hub_hash, roomN)}
                    onjoinroom={joinRoom}
                    onjoinavailableroom={joinAvailableRoom}
                    onrefreshavailablerooms={refreshAvailableRooms}
                    ontoggleavailablerooms={toggleAvailableRooms}
                    onconnecthub={connectHub}
                    ondisconnecthub={disconnectHub}
                    onopenhubsettings={openSettings}
                    onremovehub={removeHub}
                    oncopyhash={copyHash}
                    onsidebarcontextmenu={openSidebarContextMenu}
                    onreorderhubs={onReorderHubs}
                    onreorderrooms={onReorderRooms}
                    onpersistroomorder={onPersistRoomOrder}
                />
            {/if}

            <div
                class="flex min-h-0 flex-1 min-w-0 flex-col overflow-hidden bg-sem-canvas {selectedRoom
                    ? ''
                    : 'max-md:hidden'}"
            >
                {#if selectedHub && selectedRoom}
                    <RelayChatHeader
                        {selectedHub}
                        {selectedRoom}
                        {isPopoutMode}
                        {showMembers}
                        {showSearch}
                        {smUp}
                        memberCount={members.length}
                        onback={onBackFromRoom}
                        ontogglemembers={() => {
                            showMembers = !showMembers;
                        }}
                        ontogglesearch={() => {
                            showSearch = !showSearch;
                        }}
                        onopenchatprefs={openChatPrefs}
                        onpopout={popoutChannel}
                        onleaveroom={() => void leaveRoom()}
                        onclearmessages={() => void clearMessages()}
                    />

                    <div class="relative flex flex-1 min-h-0 overflow-hidden">
                        <div class="flex flex-1 min-w-0 flex-col min-h-0">
                            <div
                                bind:this={scrollContainerEl}
                                class="relative flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4"
                                style="overflow-anchor: none"
                                onscroll={onMessagesScroll}
                            >
                                <div class="relative min-w-0 {useVirtualMessageList ? '' : 'space-y-1.5'}">
                                    {#if !isLoadingPrevious && hasMorePrevious}
                                        <button
                                            type="button"
                                            class="absolute top-0 left-1/2 z-20 -translate-x-1/2 flex items-center gap-1.5 rounded-full border border-sem-border bg-sem-canvas/95 px-3 py-1 text-xs font-medium text-sem-fg-secondary shadow-xs backdrop-blur-sm hover:bg-sem-surface/60"
                                            onclick={() => void loadPreviousMessages()}
                                        >
                                            <MaterialDesignIcon iconName="arrow-up" class="size-3.5" />
                                            {t("relay_chat.load_previous")}
                                        </button>
                                    {/if}
                                    {#if useVirtualMessageList}
                                        <RelayMessageListVirtual
                                            bind:this={virtualListComp}
                                            entries={timelineEntries}
                                            getScrollElement={() => scrollContainerEl}
                                            {formatDateDividerLabel}
                                            {isPresenceGroupExpanded}
                                            {togglePresenceGroup}
                                            {formatPresenceGroupSummary}
                                            {messageKey}
                                            {renderMessageHtml}
                                            {relayMessageDisplayText}
                                            {relayMessageTranslation}
                                            {toggleRelayMessageOriginal}
                                            onmessagehtmlclick={handleMessageHtmlClick}
                                            onmessagecontextmenu={openMessageContextMenu}
                                        />
                                    {:else}
                                        {#each timelineEntries as entry, entryIndex (timelineEntryKey(entry, entryIndex))}
                                            <RelayMessageEntry
                                                {entry}
                                                {formatDateDividerLabel}
                                                {isPresenceGroupExpanded}
                                                {togglePresenceGroup}
                                                {formatPresenceGroupSummary}
                                                {messageKey}
                                                {renderMessageHtml}
                                                {relayMessageDisplayText}
                                                {relayMessageTranslation}
                                                {toggleRelayMessageOriginal}
                                                onmessagehtmlclick={handleMessageHtmlClick}
                                                onmessagecontextmenu={openMessageContextMenu}
                                            />
                                        {/each}
                                    {/if}
                                </div>
                            </div>

                            {#if !relayAtBottom && selectedRoom}
                                <div class="flex justify-center pb-1.5 pt-0.5 shrink-0">
                                    <button
                                        type="button"
                                        class="relative flex items-center justify-center size-10 min-h-[44px] min-w-[44px] rounded-full bg-sem-surface/90 backdrop-blur-sm border border-sem-border shadow-sm text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-fg transition-colors"
                                        title={t("relay_chat.scroll_to_bottom")}
                                        onclick={() => scrollToBottom()}
                                    >
                                        <MaterialDesignIcon iconName="chevron-down" class="size-5" />
                                        {#if newMessagesBelow > 0}
                                            <span
                                                class="absolute -top-1 -right-1 flex items-center justify-center min-w-5 h-5 rounded-full bg-sem-action-primary px-1 text-[10px] font-bold text-sem-action-primary-text"
                                            >
                                                {newMessagesBelow > 99 ? "99+" : newMessagesBelow}
                                            </span>
                                        {/if}
                                    </button>
                                </div>
                            {/if}

                            <RelayMessageComposer
                                bind:this={composerComp}
                                bind:text={composer}
                                {members}
                                maxlength={selectedHub?.max_msg_body_bytes || 350}
                                disabled={sending}
                                onkeydown={onComposerKeydown}
                                onsend={() => void sendMessage()}
                            />
                        </div>

                        {#if showMembers}
                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                            <div
                                class="absolute inset-0 z-30 bg-black/40 md:hidden"
                                onclick={() => {
                                    showMembers = false;
                                }}
                            ></div>
                            <RelayMembersPanel
                                {members}
                                {offlineMembers}
                                {memberDmLoadingHash}
                                onclose={() => {
                                    showMembers = false;
                                }}
                                oninsertmention={insertMention}
                                oncopymemberhash={copyMemberHash}
                                onopenmemberdm={openMemberDm}
                            />
                        {/if}

                        {#if showSearch}
                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                            <div
                                class="absolute inset-0 z-30 bg-black/40 md:hidden"
                                onclick={() => {
                                    showSearch = false;
                                }}
                            ></div>
                            <RelaySearchPanel
                                bind:searchTerm={messageSearch}
                                results={searchResults}
                                {displayName}
                                {nameStyle}
                                {formatTime}
                                onclose={() => {
                                    showSearch = false;
                                }}
                                onselectmessage={scrollToMessage}
                            />
                        {/if}
                    </div>
                {:else if selectedHub}
                    <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-sem-fg-muted">
                        <MaterialDesignIcon iconName="pound" class="size-12 opacity-30 mb-2" />
                        <div class="font-semibold text-base mb-1">{t("relay_chat.no_room_selected")}</div>
                        <p class="text-xs max-w-sm">{t("relay_chat.select_or_join_room_hint")}</p>
                    </div>
                {:else}
                    <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-sem-fg-muted">
                        <MaterialDesignIcon iconName="forum-outline" class="size-12 opacity-30 mb-2" />
                        <div class="font-semibold text-base mb-1">{t("relay_chat.welcome_title")}</div>
                        <p class="text-xs max-w-sm">{t("relay_chat.select_hub_hint")}</p>
                    </div>
                {/if}
            </div>
        </div>

        {#if view === "discovery"}
            <RelayDiscoveryView
                {discovered}
                bind:searchTerm={discoverySearch}
                isLoading={discoveryLoading}
                {isHubAdded}
                {nodeName}
                {formatHash}
                {timeAgo}
                onsearchchange={onDiscoverySearch}
                onrefresh={refreshDiscovered}
                oncopyhash={copyHash}
                onadd={addFromDiscovery}
                onopen={openDiscovered}
            />
        {:else if view === "host"}
            {#if hostModeration.hub}
                <RelayHostModerationPage
                    hub={hostModeration.hub}
                    initialTab={hostModeration.tab}
                    roomFilter={hostModeration.room}
                    onback={closeHostModeration}
                    onrefresh={fetchServers}
                />
            {:else}
                <RelayHostView
                    {serverHubs}
                    {isHubAdded}
                    uptimeFor={hostedHubUptimeSeconds}
                    {formatHash}
                    oncreatehub={() => {
                        showCreateHub = true;
                    }}
                    onjoinclient={joinHostedAsClient}
                    onleaveclient={leaveHostedAsClient}
                    onshare={(hub) => shareHubLink({ hub_hash: hub.dest_hash ?? undefined, name: hub.name || "" })}
                    onstart={startServerHub}
                    onstop={stopServerHub}
                    onopensettings={openHostHubSettings}
                    onannounce={announceServerHub}
                    ondelete={deleteServerHub}
                    onmoderate={(hub) => openHostModeration(hub)}
                    oncopyhash={copyHash}
                />
            {/if}
        {:else if view === "bots"}
            <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
                <RelayBotsPage knownHubs={botsKnownHubs} />
            </div>
        {:else if view === "search"}
            <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
                <RelaySearchPage onopenroom={openSearchResult} />
            </div>
        {/if}
    {/if}

    <RelayChatModals
        {showAddHub}
        {showCreateHub}
        {showHostHubSettings}
        {showHubSettings}
        {showChatPrefs}
        {sidebarMenu}
        {messageMenu}
        {settingsHub}
        {hostSettingsHub}
        {canModerateSelectedHub}
        {hideJoinPart}
        {highlightWords}
        {ignoredPeers}
        {applyingOptionsToAllHubs}
        oncloseaddhub={() => {
            showAddHub = false;
        }}
        onsubmitaddhub={handleAddHubSubmit}
        onclosecreatehub={() => {
            showCreateHub = false;
        }}
        onsubmitcreatehub={createServerHub}
        onclosehosthubsettings={() => {
            showHostHubSettings = false;
        }}
        onsubmithosthubsettings={saveHostHubSettings}
        onclosehubsettings={() => {
            showHubSettings = false;
        }}
        onsubmithubsettings={saveHubSettings}
        onapplyoptionsall={applyOptionsToAllHubs}
        onclosechatprefs={() => {
            showChatPrefs = false;
        }}
        onsethidejoinpart={setHideJoinPart}
        onaddhighlightword={addHighlightWord}
        onremovehighlightword={removeHighlightWord}
        onremoveignoredpeer={removeIgnoredPeer}
        onclosesidebarmenu={closeSidebarMenu}
        onclosemessagemenu={closeMessageMenu}
        onopenaddhubmenu={openAddHubFromMenu}
        onaddroommenu={focusJoinRoomFromMenu}
        onconnecthubmenu={connectHubFromMenu}
        ondisconnecthubmenu={disconnectHubFromMenu}
        onopensettingsmenu={openSettingsFromMenu}
        oncopyhubaddressmenu={copyHubAddressFromMenu}
        onsharehubmenu={shareHubFromMenu}
        onleaveroommenu={leaveRoomFromMenu}
        onremovehubmenu={removeHubFromMenu}
        {canQuoteMessage}
        {canMentionMessageAuthor}
        {canIgnoreMessageAuthor}
        {isIgnoredAuthor}
        {canTranslateRelayMessage}
        onreplyquote={replyWithQuoteFromMenu}
        onmentionuser={mentionUserFromMenu}
        oncopymessage={copyMessageFromMenu}
        ontoggleignore={toggleIgnoreFromMenu}
        ontranslatemessage={translateRelayMessageFromMenu}
        onkickuser={kickUserFromMenu}
        onbanuser={banUserFromMenu}
    />
</div>
