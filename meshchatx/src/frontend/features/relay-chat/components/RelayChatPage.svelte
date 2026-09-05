<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy, tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import GlobalState from "../../../js/GlobalState.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import WebSocketConnection from "../../../js/WebSocketConnection.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import MarkdownRenderer from "../../../js/MarkdownRenderer.js";
    import { t } from "../../../js/i18n.js";
    import {
        buildRelayMessageTimeline,
        mergeRelayMessages,
        relayMessageKey,
    } from "../../../js/relayMessageTimeline.js";
    import { loadRelayLayout, saveRelayLayout } from "../../../js/relayLayoutStore.js";
    import { loadFeatureSidebarCollapsed, saveFeatureSidebarCollapsed } from "../../../js/browserLayoutStore.js";
    import { buildRelayShareMessage } from "../../../js/relayLinkUtils.js";
    import RelayChatHeader from "./RelayChatHeader.svelte";
    import RelayHubSidebar from "./RelayHubSidebar.svelte";
    import RelayMembersPanel from "./RelayMembersPanel.svelte";
    import RelaySearchPanel from "./RelaySearchPanel.svelte";
    import RelayMessageComposer from "./RelayMessageComposer.svelte";
    import RelayMessageListVirtual from "./RelayMessageListVirtual.svelte";
    import RelayDiscoveryView from "./RelayDiscoveryView.svelte";
    import RelayHostView from "./RelayHostView.svelte";
    import RelayHostModerationPage from "./RelayHostModerationPage.svelte";
    import RelayChatModals from "./RelayChatModals.svelte";
    import { MIN_VIRTUAL_RELAY_ENTRIES } from "../lib/constants.js";
    import type {
        RrcDiscoveredHub,
        RrcHostedHub,
        RrcHub,
        RrcMember,
        RrcMessage,
        RrcRoom,
        RrcTimelineEntry,
    } from "../lib/types.js";

    interface Props {
        hubHash?: string | null;
        room?: string | null;
        isPopout?: boolean;
    }

    let { hubHash = null, room = null, isPopout = false }: Props = $props();

    let view = $state<"chat" | "discovery" | "host" | "moderation">("chat");
    let sidebarCollapsed = $state(false);
    let hubs = $state<RrcHub[]>([]);
    let selectedHubHash = $state<string | null>(null);
    let selectedRoomName = $state<string | null>(null);
    let expandedHubs = $state<Record<string, boolean>>({});
    let messagesMap = $state<Record<string, RrcMessage[]>>({});
    let membersMap = $state<Record<string, RrcMember[]>>({});
    let discoveredHubs = $state<RrcDiscoveredHub[]>([]);
    let hostedHub = $state<RrcHostedHub | null>(null);
    let showMembersPanel = $state(false);
    let showSearchPanel = $state(false);
    let expandedPresenceGroups = $state<Record<string, boolean>>({});

    // Modals
    let showAddHubModal = $state(false);
    let showCreateHostModal = $state(false);
    let showHubSettingsModal = $state(false);
    let showRoomKeyModal = $state(false);
    let editingHub = $state<RrcHub | null>(null);
    let pendingKeyRoom = $state<{ hub: RrcHub; room: string } | null>(null);
    let sidebarMenu = $state<{ show: boolean; x: number; y: number; hub?: RrcHub | null }>({ show: false, x: 0, y: 0 });
    let messageMenu = $state<{ show: boolean; x: number; y: number; msg?: RrcMessage | null }>({
        show: false,
        x: 0,
        y: 0,
    });

    let scrollContainerEl = $state<HTMLDivElement | null>(null);
    let virtualListEl = $state<RelayMessageListVirtual | null>(null);

    const rrcEnabled = $derived(GlobalState.config?.rrc_enabled ?? true);

    const tabs = [
        { id: "chat", label: "relay_chat.tab_chat", icon: "forum" },
        { id: "discovery", label: "relay_chat.tab_discovery", icon: "compass" },
        { id: "host", label: "relay_chat.tab_host", icon: "server" },
    ] as const;

    const selectedHub = $derived.by(() => {
        return hubs.find((h) => h.hub_hash === selectedHubHash) || null;
    });

    const selectedRoom = $derived.by((): RrcRoom | null => {
        if (!selectedHub || !selectedRoomName) return null;
        if (Array.isArray(selectedHub.rooms)) {
            return selectedHub.rooms.find((r) => r.name === selectedRoomName) || null;
        }
        if (selectedHub.rooms && typeof selectedHub.rooms === "object") {
            return (selectedHub.rooms as Record<string, RrcRoom>)[selectedRoomName] || null;
        }
        return null;
    });

    const currentRoomKey = $derived.by(() => {
        if (!selectedHubHash || !selectedRoomName) return "";
        return `${selectedHubHash}:${selectedRoomName}`;
    });

    const currentMessages = $derived.by(() => {
        return messagesMap[currentRoomKey] || [];
    });

    const currentMembers = $derived.by(() => {
        return membersMap[currentRoomKey] || [];
    });

    const timelineEntries = $derived.by((): RrcTimelineEntry[] => {
        return buildRelayMessageTimeline(currentMessages as any) as unknown as RrcTimelineEntry[];
    });

    const useVirtualMessageList = $derived(timelineEntries.length >= MIN_VIRTUAL_RELAY_ENTRIES);

    const canModerateSelectedHub = $derived(!!(selectedHub?.is_operator || selectedHub?.is_founder));

    function formatDateDividerLabel(dayKey?: string): string {
        return dayKey || "";
    }

    function isPresenceGroupExpanded(id?: string): boolean {
        return !!(id && expandedPresenceGroups[id]);
    }

    function togglePresenceGroup(id?: string) {
        if (id) expandedPresenceGroups[id] = !expandedPresenceGroups[id];
    }

    function formatPresenceGroupSummary(entry: RrcTimelineEntry): string {
        const count = entry.messages?.length || 0;
        return `${count} presence events`;
    }

    function renderMessageHtml(text: string): string {
        return MarkdownRenderer.renderBasic(text || "");
    }

    async function fetchHubs() {
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get("/api/v1/rrc/hubs");
            hubs = res.data?.hubs || [];
        } catch {
            hubs = [];
        }
    }

    async function fetchHostedHub() {
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get("/api/v1/rrc/servers/active");
            hostedHub = res.data?.server || null;
        } catch {
            hostedHub = null;
        }
    }

    async function fetchDiscoveredHubs() {
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get("/api/v1/rrc/discovery");
            discoveredHubs = res.data?.hubs || [];
        } catch {
            discoveredHubs = [];
        }
    }

    async function loadRoomMessages(hubH: string, rName: string) {
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get(`/api/v1/rrc/hubs/${hubH}/rooms/${encodeURIComponent(rName)}/messages`);
            const msgs = res.data?.messages || [];
            messagesMap[`${hubH}:${rName}`] = msgs;
            await tick();
            scrollToBottom();
        } catch {
            // failed
        }
    }

    async function loadRoomMembers(hubH: string, rName: string) {
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get(`/api/v1/rrc/hubs/${hubH}/rooms/${encodeURIComponent(rName)}/members`);
            membersMap[`${hubH}:${rName}`] = res.data?.members || [];
        } catch {
            // failed
        }
    }

    function selectRoom(hubObj: RrcHub, roomObj: RrcRoom) {
        selectedHubHash = hubObj.hub_hash;
        selectedRoomName = roomObj.name;
        expandedHubs[hubObj.hub_hash] = true;
        loadRoomMessages(hubObj.hub_hash, roomObj.name);
        loadRoomMembers(hubObj.hub_hash, roomObj.name);
        persistLayout();
    }

    function scrollToBottom() {
        if (useVirtualMessageList) {
            virtualListEl?.scrollToBottom();
        } else if (scrollContainerEl) {
            scrollContainerEl.scrollTop = scrollContainerEl.scrollHeight;
        }
    }

    function handleSendMessage(text: string) {
        if (!selectedHubHash || !selectedRoomName) return;
        WebSocketConnection.send({
            type: "rrc.send_message",
            hub_hash: selectedHubHash,
            room: selectedRoomName,
            text,
        });
    }

    async function handleAddHub(hubH: string, name: string, autoReconnect: boolean, icon: string) {
        showAddHubModal = false;
        const api = (window as any).api;
        if (!api) return;
        try {
            await api.post("/api/v1/rrc/hubs", {
                hub_hash: hubH,
                display_name: name || null,
                auto_reconnect: autoReconnect,
                icon,
            });
            ToastUtils.success(t("relay_chat.hub_added"));
            fetchHubs();
        } catch (e: any) {
            ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function handleRemoveHub(hubObj: RrcHub) {
        sidebarMenu.show = false;
        if (
            await DialogUtils.confirm(
                t("relay_chat.remove_hub_confirm", { name: hubObj.display_name || hubObj.hub_hash })
            )
        ) {
            const api = (window as any).api;
            if (!api) return;
            try {
                await api.delete(`/api/v1/rrc/hubs/${hubObj.hub_hash}`);
                ToastUtils.success(t("relay_chat.hub_removed"));
                if (selectedHubHash === hubObj.hub_hash) {
                    selectedHubHash = null;
                    selectedRoomName = null;
                }
                fetchHubs();
            } catch (e: any) {
                ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
            }
        }
    }

    function handleWsMessage(event: CustomEvent) {
        const data = event.detail;
        if (!data) return;

        if (data.type === "rrc.room_message" && data.hub_hash && data.room && data.message) {
            const key = `${data.hub_hash}:${data.room}`;
            const existing = messagesMap[key] || [];
            messagesMap[key] = mergeRelayMessages(existing, [data.message]) as any;
            if (key === currentRoomKey) {
                tick().then(scrollToBottom);
            }
        } else if (data.type === "rrc.hubs_updated" || data.type === "rrc.hub_status_changed") {
            fetchHubs();
        } else if (data.type === "rrc.room_members_updated" && data.hub_hash && data.room) {
            membersMap[`${data.hub_hash}:${data.room}`] = data.members || [];
        }
    }

    function persistLayout() {
        saveRelayLayout({
            selectedHubHash,
            selectedRoomName,
            expandedHubs,
            view: view === "moderation" ? "host" : view,
        });
    }

    function onIdentitySwitched() {
        hubs = [];
        selectedHubHash = null;
        selectedRoomName = null;
        messagesMap = {};
        membersMap = {};
        fetchHubs();
        fetchHostedHub();
        fetchDiscoveredHubs();
    }

    onMount(() => {
        sidebarCollapsed = loadFeatureSidebarCollapsed("relayChat") ?? false;
        fetchHubs();
        fetchHostedHub();
        fetchDiscoveredHubs();
        GlobalEmitter.on("ws-message", handleWsMessage);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);

        const saved = loadRelayLayout();
        if (saved) {
            if (saved.selectedHubHash) selectedHubHash = saved.selectedHubHash;
            if (saved.selectedRoomName) selectedRoomName = saved.selectedRoomName;
            if (saved.expandedHubs) expandedHubs = saved.expandedHubs;
        }

        if (hubHash) {
            selectedHubHash = hubHash;
            if (room) selectedRoomName = room;
            expandedHubs[hubHash] = true;
        }
    });

    onDestroy(() => {
        GlobalEmitter.off("ws-message", handleWsMessage);
        GlobalEmitter.off("identity-switched", onIdentitySwitched);
        persistLayout();
    });
</script>

<div class="flex flex-col flex-1 min-w-0 h-full bg-sem-canvas text-sem-fg">
    {#if !rrcEnabled}
        <div class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center text-sem-fg-muted">
            <MaterialDesignIcon iconName="forum-off-outline" class="size-12 opacity-40" />
            <p class="max-w-md text-sm">{t("relay_chat.disabled_message")}</p>
        </div>
    {:else if view === "moderation"}
        <RelayHostModerationPage
            hub={hostedHub}
            onback={() => {
                view = "host";
            }}
            onrefresh={fetchHostedHub}
        />
    {:else}
        {#if !isPopout}
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
                            : 'text-sem-fg-muted hover:bg-sem-surface/80'}"
                        onclick={() => {
                            view = tabItem.id as any;
                        }}
                    >
                        <MaterialDesignIcon iconName={tabItem.icon} class="size-4 shrink-0 opacity-70" />
                        <span>{t(tabItem.label)}</span>
                    </button>
                {/each}
            </div>
        {/if}

        {#if view === "chat"}
            <div class="flex flex-1 min-h-0 overflow-hidden">
                {#if !isPopout}
                    <RelayHubSidebar
                        {hubs}
                        {selectedHubHash}
                        {selectedRoomName}
                        collapsed={sidebarCollapsed}
                        {expandedHubs}
                        onaddhub={() => {
                            showAddHubModal = true;
                        }}
                        ontogglecollapse={() => {
                            sidebarCollapsed = !sidebarCollapsed;
                            saveFeatureSidebarCollapsed("relayChat", sidebarCollapsed);
                        }}
                        onselecthub={(h) => {
                            selectedHubHash = h.hub_hash;
                        }}
                        onselectroom={selectRoom}
                        onjoinroom={(h) => {
                            pendingKeyRoom = { hub: h, room: "" };
                            showRoomKeyModal = true;
                        }}
                        onhubcontextmenu={(e, h) => {
                            sidebarMenu = { show: true, x: e.clientX, y: e.clientY, hub: h };
                        }}
                        ontogglehubexpanded={(hHash) => {
                            expandedHubs[hHash] = !expandedHubs[hHash];
                        }}
                    />
                {/if}

                <div class="flex-1 flex flex-col min-h-0 bg-sem-canvas overflow-hidden">
                    {#if selectedRoom}
                        <RelayChatHeader
                            {selectedHub}
                            {selectedRoom}
                            isPopoutMode={isPopout}
                            {showMembersPanel}
                            {showSearchPanel}
                            memberCount={currentMembers.length}
                            onback={() => {
                                selectedRoomName = null;
                            }}
                            ontogglemembers={() => {
                                showMembersPanel = !showMembersPanel;
                            }}
                            ontogglesearch={() => {
                                showSearchPanel = !showSearchPanel;
                            }}
                            onshare={() => {
                                if (selectedHubHash && selectedRoomName) {
                                    const msg = buildRelayShareMessage({
                                        hub: selectedHubHash,
                                        room: selectedRoomName,
                                    });
                                    if (msg) {
                                        navigator.clipboard?.writeText(msg);
                                        ToastUtils.success(t("relay_chat.copied_share_link"));
                                    }
                                }
                            }}
                            onpopout={() => {
                                const target = `/popout/relay-chat/${selectedHubHash}/${selectedRoomName}`;
                                window.open(target, "_blank", "width=960,height=720");
                            }}
                            onleaveroom={async () => {
                                if (
                                    await DialogUtils.confirm(
                                        t("relay_chat.leave_room_confirm", { room: selectedRoomName })
                                    )
                                ) {
                                    WebSocketConnection.send({
                                        type: "rrc.leave_room",
                                        hub_hash: selectedHubHash,
                                        room: selectedRoomName,
                                    });
                                    selectedRoomName = null;
                                }
                            }}
                        />

                        <div class="flex flex-1 min-h-0 overflow-hidden">
                            <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
                                <div bind:this={scrollContainerEl} class="flex-1 overflow-y-auto p-3 space-y-1">
                                    {#if useVirtualMessageList}
                                        <RelayMessageListVirtual
                                            bind:this={virtualListEl}
                                            entries={timelineEntries}
                                            getScrollElement={() => scrollContainerEl}
                                            {formatDateDividerLabel}
                                            {isPresenceGroupExpanded}
                                            {togglePresenceGroup}
                                            {formatPresenceGroupSummary}
                                            messageKey={(m) => (m ? relayMessageKey(m) : "")}
                                            {renderMessageHtml}
                                            onmessagecontextmenu={(e, msg) => {
                                                e.preventDefault();
                                                messageMenu = { show: true, x: e.clientX, y: e.clientY, msg };
                                            }}
                                        />
                                    {:else}
                                        {#each timelineEntries as entry (entry.id || (entry.msg ? relayMessageKey(entry.msg) : entry.type))}
                                            <RelayMessageListVirtual
                                                entries={[entry]}
                                                getScrollElement={() => scrollContainerEl}
                                                {formatDateDividerLabel}
                                                {isPresenceGroupExpanded}
                                                {togglePresenceGroup}
                                                {formatPresenceGroupSummary}
                                                messageKey={(m) => (m ? relayMessageKey(m) : "")}
                                                {renderMessageHtml}
                                                onmessagecontextmenu={(e, msg) => {
                                                    e.preventDefault();
                                                    messageMenu = { show: true, x: e.clientX, y: e.clientY, msg };
                                                }}
                                            />
                                        {/each}
                                    {/if}
                                </div>

                                <RelayMessageComposer members={currentMembers} onsend={handleSendMessage} />
                            </div>

                            {#if showMembersPanel}
                                <RelayMembersPanel
                                    members={currentMembers}
                                    canModerate={canModerateSelectedHub}
                                    onclose={() => {
                                        showMembersPanel = false;
                                    }}
                                />
                            {/if}

                            {#if showSearchPanel}
                                <RelaySearchPanel
                                    messages={currentMessages}
                                    onclose={() => {
                                        showSearchPanel = false;
                                    }}
                                    onselectmessage={(m) => {
                                        virtualListEl?.scrollToMessageKey(relayMessageKey(m));
                                    }}
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
        {:else if view === "discovery"}
            <RelayDiscoveryView
                {discoveredHubs}
                onrefresh={fetchDiscoveredHubs}
                onconnect={(h) => {
                    const hubHash = h.hub_hash || h.destination_hash || "";
                    if (hubHash) {
                        handleAddHub(hubHash, h.name || h.display_name || "", true, "forum");
                        view = "chat";
                    }
                }}
                oncopyhash={(h) => {
                    navigator.clipboard.writeText(h);
                    ToastUtils.success(t("relay_chat.copied_hub_hash"));
                }}
            />
        {:else if view === "host"}
            <RelayHostView
                {hostedHub}
                oncreatehub={() => {
                    showCreateHostModal = true;
                }}
                ontogglestart={async () => {
                    const api = (window as any).api;
                    if (!api) return;
                    try {
                        if (hostedHub?.running) {
                            await api.post("/api/v1/rrc/servers/stop");
                        } else {
                            await api.post("/api/v1/rrc/servers/start");
                        }
                        fetchHostedHub();
                    } catch (e: any) {
                        ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
                    }
                }}
                onopenmoderation={() => {
                    view = "moderation";
                }}
                onopensettings={() => {
                    showCreateHostModal = true;
                }}
                oncopyhash={(h) => {
                    navigator.clipboard.writeText(h);
                    ToastUtils.success(t("relay_chat.copied_hub_hash"));
                }}
            />
        {/if}
    {/if}

    <RelayChatModals
        {showAddHubModal}
        {showCreateHostModal}
        {showHubSettingsModal}
        {showRoomKeyModal}
        {editingHub}
        {sidebarMenu}
        {messageMenu}
        {canModerateSelectedHub}
        oncloseaddhub={() => {
            showAddHubModal = false;
        }}
        onsubmitaddhub={handleAddHub}
        onclosecreatehost={() => {
            showCreateHostModal = false;
        }}
        onsubmitcreatehost={async (name, announceInterval) => {
            showCreateHostModal = false;
            const api = (window as any).api;
            if (!api) return;
            try {
                await api.post("/api/v1/rrc/servers", { name, announce_interval: announceInterval });
                ToastUtils.success(t("relay_chat.host_hub_saved"));
                fetchHostedHub();
            } catch (e: any) {
                ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
            }
        }}
        onclosehubsettings={() => {
            showHubSettingsModal = false;
        }}
        onsubmithubsettings={async (hubObj, name, autoReconnect, icon) => {
            showHubSettingsModal = false;
            const api = (window as any).api;
            if (!api) return;
            try {
                await api.put(`/api/v1/rrc/hubs/${hubObj.hub_hash}`, {
                    custom_display_name: name || null,
                    auto_reconnect: autoReconnect,
                    icon,
                });
                ToastUtils.success(t("relay_chat.hub_updated"));
                fetchHubs();
            } catch (e: any) {
                ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
            }
        }}
        onremovehub={handleRemoveHub}
        oncloseroomkey={() => {
            showRoomKeyModal = false;
        }}
        onsubmitroomkey={(key) => {
            showRoomKeyModal = false;
            if (pendingKeyRoom) {
                WebSocketConnection.send({
                    type: "rrc.join_room",
                    hub_hash: pendingKeyRoom.hub.hub_hash,
                    room: pendingKeyRoom.room,
                    key: key || null,
                });
                pendingKeyRoom = null;
            }
        }}
        onclosesidebarmenu={() => {
            sidebarMenu.show = false;
        }}
        onclosemessagemenu={() => {
            messageMenu.show = false;
        }}
        oncopytext={(txt) => {
            navigator.clipboard?.writeText(txt);
            ToastUtils.success(t("messages.copied_to_clipboard"));
        }}
        oncopylink={(h) => {
            const msg = buildRelayShareMessage({ hub: h.hub_hash });
            if (msg) {
                navigator.clipboard?.writeText(msg);
                ToastUtils.success(t("relay_chat.copied_share_link"));
            }
        }}
        onkickmessageauthor={async (msg) => {
            if (!selectedHubHash || !selectedRoomName || !msg.src) return;
            const api = (window as any).api;
            if (!api) return;
            try {
                await api.post(`/api/v1/rrc/servers/${selectedHubHash}/moderate`, {
                    action: "kick",
                    peer: msg.src,
                    room: selectedRoomName,
                });
                ToastUtils.success(t("relay_chat.host_moderation_success"));
            } catch (e: any) {
                ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
            }
        }}
        onbanmessageauthor={async (msg) => {
            if (!selectedHubHash || !selectedRoomName || !msg.src) return;
            const api = (window as any).api;
            if (!api) return;
            try {
                await api.post(`/api/v1/rrc/servers/${selectedHubHash}/moderate`, {
                    action: "ban",
                    peer: msg.src,
                    room: selectedRoomName,
                });
                ToastUtils.success(t("relay_chat.host_moderation_success"));
            } catch (e: any) {
                ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
            }
        }}
    />
</div>
