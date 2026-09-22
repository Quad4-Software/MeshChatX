<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy, untrack } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import SearchInput from "../../../ui/svelte/SearchInput.svelte";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import {
        RELAY_HOST_PAGE_HEADER,
        RELAY_HOST_PAGE_TABS,
        RELAY_HOST_PAGE_TAB,
        RELAY_HOST_PAGE_TAB_ACTIVE,
        RELAY_HOST_PAGE_TAB_IDLE,
        RELAY_HOST_PAGE_BODY,
        RELAY_HOST_PAGE_LIST,
        RELAY_HOST_PAGE_DETAIL,
        RELAY_HOST_LIST_ITEM,
        RELAY_HOST_LIST_ITEM_SELECTED,
        RELAY_HOST_LIST_ITEM_IDLE,
        RELAY_HOST_DETAIL_HEADER,
        RELAY_HOST_MESSAGE,
        RELAY_HOST_ICON_BTN,
    } from "../../../js/relayHostModerationClasses.js";
    import { formatUptime, colorForHash, memberInitial, memberAvatarStyle } from "../lib/relayFormatters.js";
    import { BTN_PRIMARY, BTN_SECONDARY } from "../lib/constants.js";
    import type { RrcHostedHub } from "../lib/types.js";

    type Tab = "rooms" | "members" | "status";
    type RoomActivity = {
        name: string;
        members?: number;
        member_count?: number;
        topic?: string;
        has_key?: boolean;
        registered?: boolean;
        message_count?: number;
    };
    type HostMember = { hash?: string; name?: string; rooms?: string[]; [key: string]: unknown };
    type HostEvent = { ts?: number; type?: string; peer?: string; room?: string; reason?: string };
    type HostMessage = { ts?: number; peer?: string; nick?: string; room?: string; text?: string };

    interface Props {
        hub?: (RrcHostedHub & { id?: string }) | null;
        initialTab?: Tab;
        roomFilter?: string | null;
        onback?: () => void;
        onrefresh?: () => void;
    }

    let { hub = null, initialTab = "rooms", roomFilter = null, onback, onrefresh }: Props = $props();

    let tab = $state<Tab>("rooms");
    let roomsActivity = $state<RoomActivity[]>([]);
    let recentActivity = $state<HostMessage[]>([]);
    let roomsSearch = $state("");
    let roomsLoading = $state(false);
    let showAddRoomForm = $state(false);
    let creatingRoom = $state(false);
    let newRoom = $state({ name: "", topic: "", key: "" });
    let selectedRoom = $state<string | null>(null);
    let members = $state<HostMember[]>([]);
    let membersSearch = $state("");
    let selectedMember = $state<HostMember | null>(null);
    let memberMessages = $state<HostMessage[]>([]);
    let messagesLoading = $state(false);
    let stats = $state<Record<string, unknown> | null>(null);
    let statsLoading = $state(false);
    let localIdentityHash = $state<string | null>(null);
    let liveUptimeSeconds = $state(0);
    let isNarrow = $state(false);

    let uptimeTimer: ReturnType<typeof setInterval> | null = null;
    let mediaQuery: MediaQueryList | null = null;
    let lastHubId = "";

    const api = () => (window as any).api;

    const hubId = $derived(hub?.id || hub?.dest_hash || "");
    const pageTitle = $derived.by(() => {
        const base = t("relay_chat.host_moderation_title");
        if (!hub?.name) return base;
        if (roomFilter && roomFilter !== "0") {
            return t("relay_chat.host_moderation_title_room", { hub: hub.name, room: roomFilter });
        }
        return t("relay_chat.host_moderation_title_hub", { hub: hub.name });
    });
    const filteredRooms = $derived.by(() => {
        const s = roomsSearch.trim().toLowerCase();
        if (!s) return roomsActivity;
        return roomsActivity.filter(
            (r) =>
                String(r.name || "")
                    .toLowerCase()
                    .includes(s) || (r.topic || "").toLowerCase().includes(s)
        );
    });
    const selectedRoomObj = $derived(roomsActivity.find((r) => r.name === selectedRoom) || null);
    const roomMessages = $derived(recentActivity.filter((m) => m.room === selectedRoom));
    const filteredMembers = $derived.by(() => {
        const s = membersSearch.trim().toLowerCase();
        if (!s) return members;
        return members.filter((m) => memberMatches(m, s));
    });
    const moderationRooms = $derived.by(() => {
        const rooms = new Set<string>();
        for (const m of members) {
            for (const r of m.rooms || []) {
                if (r) rooms.add(r);
            }
        }
        return Array.from(rooms).sort();
    });
    const statusEvents = $derived(((stats?.events as HostEvent[] | undefined) || []).slice().reverse());
    const statCards = $derived.by(() => {
        const s = stats || {};
        const num = (v: unknown) => Number(v ?? 0);
        const drops = num(s.drops_peer_cap) + num(s.drops_session_cap) + num(s.drops_rate_limited);
        const moderation = num(s.kicks) + num(s.bans) + num(s.room_bans);
        return [
            { key: "sessions", value: num(s.sessions) },
            { key: "links", value: num(s.links_total) },
            { key: "messages", value: num(s.messages_relayed) },
            { key: "drops", value: drops },
            { key: "moderation", value: moderation },
            { key: "uptime", value: formatUptime(num(s.uptime_s)) },
        ];
    });

    function memberMatches(m: HostMember, s: string): boolean {
        const nick = String(m.name || "").toLowerCase();
        const hash = String(m.hash || "").toLowerCase();
        return nick.includes(s) || hash.includes(s);
    }

    function formatHash(h?: string | null): string {
        return h ? `${h.slice(0, 10)}..${h.slice(-4)}` : "";
    }

    function avatarCss(hash?: string | null): string {
        const st = memberAvatarStyle(hash);
        return `background-color: ${st.backgroundColor}; color: ${st.color};`;
    }

    function relativeTime(ts?: number | string): string {
        if (!ts) return "";
        const d = new Date(ts);
        const diff = Date.now() - d.getTime();
        if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
        if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
        if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
        return d.toLocaleString();
    }

    async function fetchActivity() {
        if (!hubId) return;
        roomsLoading = true;
        try {
            const res = await api()?.get(`/api/v1/rrc/servers/${hubId}/activity`);
            roomsActivity = res?.data?.rooms || [];
            recentActivity = res?.data?.recent || [];
        } catch {
            roomsActivity = [];
            recentActivity = [];
        } finally {
            roomsLoading = false;
        }
    }

    async function fetchMembers() {
        if (!hubId) return;
        try {
            const res = await api()?.get(`/api/v1/rrc/servers/${hubId}/members`);
            members = res?.data?.members || [];
        } catch {
            members = [];
        }
    }

    async function fetchStats() {
        if (!hubId) return;
        statsLoading = true;
        try {
            const res = await api()?.get(`/api/v1/rrc/servers/${hubId}/stats`);
            stats = res?.data || null;
        } catch {
            stats = null;
        } finally {
            statsLoading = false;
        }
    }

    async function ensureLocalIdentity() {
        if (localIdentityHash) return;
        try {
            const res = await api()?.get("/api/v1/config");
            const hash = res?.data?.identity_hash;
            if (typeof hash === "string" && hash.trim()) {
                localIdentityHash = hash.trim().toLowerCase();
            }
        } catch {
            // identity lookup is best effort
        }
    }

    async function reload() {
        if (!hubId) {
            members = [];
            roomsActivity = [];
            recentActivity = [];
            stats = null;
            return;
        }
        const jobs: Promise<void>[] = [fetchMembers(), ensureLocalIdentity()];
        if (tab === "rooms") jobs.push(fetchActivity());
        else if (tab === "status") jobs.push(fetchStats());
        await Promise.all(jobs);
    }

    function setTab(next: Tab) {
        tab = next;
        if (next === "rooms") fetchActivity();
        else if (next === "status") fetchStats();
    }

    function eventLabel(ev: HostEvent): string {
        const key = `relay_chat.host_ev_${ev.type}`;
        const val = t(key);
        return val === key ? String(ev.type || "") : val;
    }

    function isWarningEvent(ev: HostEvent): boolean {
        return ["rate_limited", "peer_cap_drop", "session_cap_drop", "banned_disconnect"].includes(String(ev.type));
    }

    async function createRoom() {
        if (!hubId || !newRoom.name.trim()) return;
        creatingRoom = true;
        try {
            await api()?.post(`/api/v1/rrc/servers/${hubId}/rooms`, {
                name: newRoom.name.trim(),
                topic: newRoom.topic.trim() || null,
                key: newRoom.key || null,
            });
            ToastUtils.success(t("relay_chat.host_room_created"));
            newRoom = { name: "", topic: "", key: "" };
            showAddRoomForm = false;
            fetchActivity();
            onrefresh?.();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        } finally {
            creatingRoom = false;
        }
    }

    function cancelAddRoom() {
        showAddRoomForm = false;
        newRoom = { name: "", topic: "", key: "" };
    }

    async function setRoomKey() {
        if (!hubId || !selectedRoom) return;
        const key = await DialogUtils.prompt(t("relay_chat.host_room_key_prompt", { room: selectedRoom }));
        if (!key || !key.trim()) return;
        try {
            await api()?.put(`/api/v1/rrc/servers/${hubId}/rooms/${encodeURIComponent(selectedRoom)}/key`, {
                key: key.trim(),
            });
            ToastUtils.success(t("relay_chat.host_room_key_saved"));
            fetchActivity();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function clearRoomKey() {
        if (!hubId || !selectedRoom) return;
        if (!(await DialogUtils.confirm(t("relay_chat.host_clear_room_key_confirm")))) return;
        try {
            await api()?.delete(`/api/v1/rrc/servers/${hubId}/rooms/${encodeURIComponent(selectedRoom)}/key`);
            ToastUtils.success(t("relay_chat.host_room_key_cleared"));
            fetchActivity();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function deleteRoom(roomName: string) {
        if (!hubId || !(await DialogUtils.confirm(t("relay_chat.host_delete_room_confirm")))) return;
        try {
            await api()?.delete(`/api/v1/rrc/servers/${hubId}/rooms/${encodeURIComponent(roomName)}`);
            ToastUtils.success(t("relay_chat.host_room_deleted"));
            if (selectedRoom === roomName) selectedRoom = null;
            fetchActivity();
            onrefresh?.();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function loadMemberMessages(member: HostMember) {
        selectedMember = member;
        if (!hubId || !member?.hash) return;
        messagesLoading = true;
        try {
            const params: Record<string, unknown> = { peer: member.hash, limit: 200 };
            if (roomFilter && roomFilter !== "0") params.room = roomFilter;
            const res = await api()?.get(`/api/v1/rrc/servers/${hubId}/messages`, { params });
            memberMessages = res?.data?.messages || [];
        } catch {
            memberMessages = [];
        } finally {
            messagesLoading = false;
        }
    }

    async function resolveModerationRoom(member: HostMember, action: string): Promise<string | null> {
        const memberRooms = (member?.rooms || []).filter(Boolean);
        const roomSet = new Set<string>(memberRooms);
        for (const r of moderationRooms) roomSet.add(r);
        const rooms = Array.from(roomSet).filter(Boolean);
        if (rooms.length === 0) {
            ToastUtils.error(t("relay_chat.host_kick_no_room"));
            return null;
        }
        if (rooms.length === 1) return rooms[0];

        const displayName = member?.name || formatHash(member?.hash);
        const choice = await DialogUtils.prompt(
            t("relay_chat.host_kick_pick_room", { name: displayName, rooms: rooms.join(", ") })
        );
        if (choice === null || choice === undefined) return null;
        const trimmed = String(choice).trim().replace(/^#/, "");
        if (roomSet.has(trimmed) || rooms.includes(trimmed)) return trimmed;
        ToastUtils.error(t("relay_chat.host_kick_room_invalid"));
        return null;
    }

    async function moderate(member: HostMember, action: string) {
        if (!hubId || !member?.hash) return;
        await ensureLocalIdentity();
        if (localIdentityHash && member.hash.toLowerCase() === localIdentityHash) {
            ToastUtils.warning(t("relay_chat.host_cannot_moderate_self"));
            return;
        }

        const displayName = member.name || formatHash(member.hash);
        let room: string | null = null;

        if (action === "ban") {
            if (!(await DialogUtils.confirm(t("relay_chat.host_ban_confirm", { name: displayName })))) return;
        } else if (action === "room_ban") {
            room = await resolveModerationRoom(member, action);
            if (!room) return;
            if (!(await DialogUtils.confirm(t("relay_chat.host_room_ban_confirm", { name: displayName, room }))))
                return;
        } else {
            room = await resolveModerationRoom(member, action);
            if (!room) return;
            if (!(await DialogUtils.confirm(t("relay_chat.host_kick_confirm", { name: displayName, room })))) return;
        }

        try {
            await api()?.post(`/api/v1/rrc/servers/${hubId}/moderate`, {
                action,
                peer: member.hash,
                room,
            });
            ToastUtils.success(t("relay_chat.host_moderation_success"));
            fetchMembers();
            onrefresh?.();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    $effect(() => {
        const id = hubId;
        untrack(() => {
            if (id && id !== lastHubId) {
                lastHubId = id;
                tab = initialTab;
                reload();
            }
        });
    });

    onMount(() => {
        liveUptimeSeconds = hub?.uptime_seconds ?? 0;
        uptimeTimer = setInterval(() => {
            if (hub?.running) liveUptimeSeconds += 1;
        }, 1000);
        if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
            mediaQuery = window.matchMedia("(max-width: 1023px)");
            const update = () => {
                isNarrow = !!mediaQuery?.matches;
            };
            update();
            mediaQuery.onchange = update;
        }
    });

    onDestroy(() => {
        if (uptimeTimer) clearInterval(uptimeTimer);
        if (mediaQuery) mediaQuery.onchange = null;
    });
</script>

<div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-sem-canvas text-sem-fg">
    <div class={RELAY_HOST_PAGE_HEADER}>
        <button type="button" class={RELAY_HOST_ICON_BTN} title={t("common.back")} onclick={() => onback?.()}>
            <MaterialDesignIcon iconName="arrow-left" class="size-5" />
        </button>
        <div class="min-w-0 flex-1">
            <h2 class="truncate text-sm font-bold text-sem-fg">{pageTitle}</h2>
            <div class="flex flex-wrap items-center gap-x-2 text-xs text-sem-fg-muted">
                <span class="inline-flex items-center gap-1.5">
                    <span class="size-2 rounded-full {hub?.running ? 'bg-emerald-500' : 'bg-zinc-400'}"></span>
                    {hub?.running ? t("relay_chat.host_status_running") : t("relay_chat.host_status_stopped")}
                </span>
                {#if hub?.running && liveUptimeSeconds > 0}
                    <span>· {t("relay_chat.host_moderation_uptime", { time: formatUptime(liveUptimeSeconds) })}</span>
                {/if}
            </div>
        </div>
    </div>

    {#if hub}
        <div class={RELAY_HOST_PAGE_TABS} role="tablist">
            <button
                type="button"
                role="tab"
                aria-selected={tab === "rooms"}
                class="{RELAY_HOST_PAGE_TAB} {tab === 'rooms' ? RELAY_HOST_PAGE_TAB_ACTIVE : RELAY_HOST_PAGE_TAB_IDLE}"
                onclick={() => setTab("rooms")}
            >
                <MaterialDesignIcon iconName="pound" class="size-4" />
                <span>{t("relay_chat.host_moderation_tab_rooms")}</span>
            </button>
            <button
                type="button"
                role="tab"
                aria-selected={tab === "members"}
                class="{RELAY_HOST_PAGE_TAB} {tab === 'members'
                    ? RELAY_HOST_PAGE_TAB_ACTIVE
                    : RELAY_HOST_PAGE_TAB_IDLE}"
                onclick={() => setTab("members")}
            >
                <MaterialDesignIcon iconName="account-group" class="size-4" />
                <span>{t("relay_chat.host_moderation_tab_members")}</span>
            </button>
            <button
                type="button"
                role="tab"
                aria-selected={tab === "status"}
                class="{RELAY_HOST_PAGE_TAB} {tab === 'status' ? RELAY_HOST_PAGE_TAB_ACTIVE : RELAY_HOST_PAGE_TAB_IDLE}"
                onclick={() => setTab("status")}
            >
                <MaterialDesignIcon iconName="chart-box" class="size-4" />
                <span>{t("relay_chat.host_moderation_tab_status")}</span>
            </button>
        </div>
    {/if}

    {#if !hub}
        <div class="flex flex-1 items-center justify-center p-6 text-sm text-sem-fg-muted">
            {t("relay_chat.host_moderation_hub_missing")}
        </div>
    {:else if tab === "rooms"}
        <div class={RELAY_HOST_PAGE_BODY}>
            <div class="{RELAY_HOST_PAGE_LIST} {isNarrow && selectedRoom ? 'hidden' : 'flex flex-1 lg:flex-none'}">
                <div class="shrink-0 space-y-3 border-b border-sem-border p-3 sm:p-4">
                    <SearchInput
                        bind:value={roomsSearch}
                        compact
                        type="search"
                        placeholder={t("relay_chat.host_rooms_search")}
                    />
                    {#if !showAddRoomForm}
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 rounded-xl border-2 border-dashed border-sem-border px-3 py-3 text-left text-sm text-sem-fg-muted transition-colors hover:border-sem-accent hover:bg-sem-surface/40 hover:text-sem-accent"
                            onclick={() => (showAddRoomForm = true)}
                        >
                            <MaterialDesignIcon iconName="plus-circle-outline" class="size-5 shrink-0" />
                            <span class="font-medium">{t("relay_chat.host_add_room")}</span>
                        </button>
                    {:else}
                        <form
                            class="space-y-2.5 rounded-xl border border-sem-border bg-sem-surface-raised/40 p-3"
                            onsubmit={(e) => {
                                e.preventDefault();
                                createRoom();
                            }}
                        >
                            <input
                                bind:value={newRoom.name}
                                type="text"
                                placeholder={t("relay_chat.host_room_name")}
                                class="input-field w-full py-2.5! text-sm!"
                            />
                            <input
                                bind:value={newRoom.topic}
                                type="text"
                                placeholder={t("relay_chat.host_room_topic")}
                                class="input-field w-full py-2.5! text-sm!"
                            />
                            <input
                                bind:value={newRoom.key}
                                type="password"
                                placeholder={t("relay_chat.host_room_key_placeholder")}
                                autocomplete="off"
                                class="input-field w-full py-2.5! text-sm!"
                            />
                            <div class="flex gap-2 pt-0.5">
                                <button
                                    type="submit"
                                    class="{BTN_PRIMARY} flex-1 py-2.5! text-sm!"
                                    disabled={creatingRoom}
                                >
                                    <MaterialDesignIcon iconName="plus" class="size-4" />
                                    {t("relay_chat.host_add_room")}
                                </button>
                                <button
                                    type="button"
                                    class="{BTN_SECONDARY} py-2.5! text-sm!"
                                    disabled={creatingRoom}
                                    onclick={cancelAddRoom}
                                >
                                    {t("common.cancel")}
                                </button>
                            </div>
                        </form>
                    {/if}
                </div>
                <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                    {#if roomsLoading}
                        <div class="py-12 text-center text-sm text-sem-fg-muted">{t("common.loading")}</div>
                    {:else if filteredRooms.length === 0}
                        <div class="py-12 text-center text-sm text-sem-fg-muted">
                            {roomsSearch.trim()
                                ? t("relay_chat.host_rooms_search_empty")
                                : t("relay_chat.host_no_rooms")}
                        </div>
                    {:else}
                        <ul class="space-y-1.5">
                            {#each filteredRooms as room (room.name)}
                                <li
                                    class="{RELAY_HOST_LIST_ITEM} {selectedRoom === room.name
                                        ? RELAY_HOST_LIST_ITEM_SELECTED
                                        : RELAY_HOST_LIST_ITEM_IDLE}"
                                >
                                    <div class="flex items-start justify-between gap-2">
                                        <button
                                            type="button"
                                            class="min-w-0 flex-1 cursor-pointer text-left"
                                            onclick={() => (selectedRoom = room.name)}
                                        >
                                            <div class="min-w-0">
                                                <div class="flex items-center gap-1.5 font-medium text-sem-fg">
                                                    <span>#{room.name}</span>
                                                    {#if room.has_key}
                                                        <span
                                                            class="inline-flex"
                                                            title={t("relay_chat.host_room_keyed")}
                                                        >
                                                            <MaterialDesignIcon
                                                                iconName="lock"
                                                                class="size-3.5 shrink-0 text-sem-fg-muted"
                                                            />
                                                        </span>
                                                    {/if}
                                                </div>
                                                {#if room.topic}
                                                    <div class="truncate text-xs text-sem-fg-muted">{room.topic}</div>
                                                {/if}
                                                <div class="mt-1 flex flex-wrap gap-x-3 text-xs text-sem-fg-muted">
                                                    <span
                                                        >{room.members ?? room.member_count ?? 0}
                                                        {t("relay_chat.host_clients")}</span
                                                    >
                                                    <span>{room.message_count || 0} msgs</span>
                                                </div>
                                            </div>
                                        </button>
                                        {#if room.registered}
                                            <button
                                                type="button"
                                                class="shrink-0 rounded-lg p-1.5 text-sem-fg-muted hover:text-sem-danger"
                                                title={t("relay_chat.host_delete_room")}
                                                onclick={(e) => {
                                                    e.stopPropagation();
                                                    deleteRoom(room.name);
                                                }}
                                            >
                                                <MaterialDesignIcon iconName="trash-can-outline" class="size-4" />
                                            </button>
                                        {/if}
                                    </div>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
            </div>

            <div class="{RELAY_HOST_PAGE_DETAIL} {isNarrow && !selectedRoom ? 'hidden' : 'flex'}">
                {#if isNarrow && selectedRoom}
                    <div class="flex shrink-0 items-center gap-2 border-b border-sem-border px-3 py-2 lg:hidden">
                        <button type="button" class={RELAY_HOST_ICON_BTN} onclick={() => (selectedRoom = null)}>
                            <MaterialDesignIcon iconName="arrow-left" class="size-5" />
                        </button>
                        <span class="font-semibold text-sem-fg">#{selectedRoom}</span>
                    </div>
                {/if}
                {#if !selectedRoom}
                    <div
                        class="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-sem-fg-muted"
                    >
                        <MaterialDesignIcon iconName="pound" class="size-10 opacity-40" />
                        {t("relay_chat.host_rooms_select")}
                    </div>
                {:else}
                    <div class="{RELAY_HOST_DETAIL_HEADER} hidden lg:block">
                        <div class="font-semibold text-sem-fg">#{selectedRoom}</div>
                        <div class="text-xs text-sem-fg-muted">{t("relay_chat.host_room_activity")}</div>
                    </div>
                    {#if selectedRoomObj}
                        <div
                            class="flex flex-wrap items-center gap-2 border-b border-sem-border px-3 py-2 text-xs text-sem-fg-muted"
                        >
                            <MaterialDesignIcon
                                iconName={selectedRoomObj.has_key ? "lock" : "lock-open-variant"}
                                class="size-4 shrink-0"
                            />
                            <span class="flex-1">
                                {selectedRoomObj.has_key
                                    ? t("relay_chat.host_room_keyed")
                                    : t("relay_chat.host_room_unkeyed")}
                            </span>
                            <button
                                type="button"
                                class="font-medium text-sem-accent hover:underline"
                                onclick={setRoomKey}
                            >
                                {selectedRoomObj.has_key
                                    ? t("relay_chat.host_change_room_key")
                                    : t("relay_chat.host_set_room_key")}
                            </button>
                            {#if selectedRoomObj.has_key}
                                <button
                                    type="button"
                                    class="font-medium text-sem-danger hover:underline"
                                    onclick={clearRoomKey}
                                >
                                    {t("relay_chat.host_clear_room_key")}
                                </button>
                            {/if}
                        </div>
                    {/if}
                    <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                        {#if roomMessages.length > 0}
                            <ul class="space-y-2">
                                {#each roomMessages as msg, idx (idx)}
                                    <li class={RELAY_HOST_MESSAGE}>
                                        <div class="flex flex-wrap items-center gap-x-2 text-xs text-sem-fg-muted">
                                            <span style="color: {colorForHash(msg.peer)}"
                                                >{msg.nick || formatHash(msg.peer)}</span
                                            >
                                            <span>{relativeTime(msg.ts)}</span>
                                        </div>
                                        <div class="mt-1 whitespace-pre-wrap wrap-break-word">{msg.text}</div>
                                    </li>
                                {/each}
                            </ul>
                        {:else}
                            <div class="py-8 text-center text-sm text-sem-fg-muted">
                                {t("relay_chat.host_no_activity")}
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        </div>
    {:else if tab === "members"}
        <div class={RELAY_HOST_PAGE_BODY}>
            <div class="{RELAY_HOST_PAGE_LIST} {isNarrow && selectedMember ? 'hidden' : 'flex flex-1 lg:flex-none'}">
                <div class="shrink-0 border-b border-sem-border p-3 sm:p-4">
                    <SearchInput
                        bind:value={membersSearch}
                        compact
                        type="search"
                        placeholder={t("relay_chat.host_members_search")}
                    />
                </div>
                <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                    {#if filteredMembers.length === 0}
                        <div class="py-12 text-center text-sm text-sem-fg-muted">
                            {t("relay_chat.no_members_found")}
                        </div>
                    {:else}
                        <ul class="space-y-1.5">
                            {#each filteredMembers as member (member.hash)}
                                <li
                                    class="px-3 py-2 {RELAY_HOST_LIST_ITEM} {selectedMember === member
                                        ? RELAY_HOST_LIST_ITEM_SELECTED
                                        : RELAY_HOST_LIST_ITEM_IDLE}"
                                >
                                    <div class="flex items-center gap-2.5">
                                        <button
                                            type="button"
                                            class="flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 text-left"
                                            onclick={() => loadMemberMessages(member)}
                                        >
                                            <span
                                                class="flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
                                                style={avatarCss(member.hash)}
                                            >
                                                {memberInitial(member.hash)}
                                            </span>
                                            <span class="min-w-0">
                                                <span class="block truncate text-sm font-medium text-sem-fg">
                                                    {member.name || formatHash(member.hash)}
                                                </span>
                                                <span class="block truncate font-mono text-[10px] text-sem-fg-muted">
                                                    {formatHash(member.hash)}
                                                </span>
                                                {#if member.rooms && member.rooms.length}
                                                    <span class="mt-0.5 flex flex-wrap gap-1">
                                                        {#each member.rooms as room (room)}
                                                            <span
                                                                class="rounded bg-sem-surface-raised px-1 py-px text-[10px] text-sem-fg-muted"
                                                                >#{room}</span
                                                            >
                                                        {/each}
                                                    </span>
                                                {/if}
                                            </span>
                                        </button>
                                        <div class="flex shrink-0 items-center gap-0.5">
                                            <button
                                                type="button"
                                                class={RELAY_HOST_ICON_BTN}
                                                title={t("relay_chat.kick_member")}
                                                onclick={(e) => {
                                                    e.stopPropagation();
                                                    moderate(member, "kick");
                                                }}
                                            >
                                                <MaterialDesignIcon iconName="account-remove" class="size-4" />
                                            </button>
                                            <button
                                                type="button"
                                                class={RELAY_HOST_ICON_BTN}
                                                title={t("relay_chat.ban_member")}
                                                onclick={(e) => {
                                                    e.stopPropagation();
                                                    moderate(member, "ban");
                                                }}
                                            >
                                                <MaterialDesignIcon iconName="cancel" class="size-4" />
                                            </button>
                                            <button
                                                type="button"
                                                class={RELAY_HOST_ICON_BTN}
                                                title={t("relay_chat.ctx_room_ban")}
                                                onclick={(e) => {
                                                    e.stopPropagation();
                                                    moderate(member, "room_ban");
                                                }}
                                            >
                                                <MaterialDesignIcon iconName="pound-box" class="size-4" />
                                            </button>
                                        </div>
                                    </div>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
            </div>

            <div class="{RELAY_HOST_PAGE_DETAIL} {isNarrow && !selectedMember ? 'hidden' : 'flex'}">
                {#if isNarrow && selectedMember}
                    <div class="flex shrink-0 items-center gap-2 border-b border-sem-border px-3 py-2 lg:hidden">
                        <button type="button" class={RELAY_HOST_ICON_BTN} onclick={() => (selectedMember = null)}>
                            <MaterialDesignIcon iconName="arrow-left" class="size-5" />
                        </button>
                        <span class="truncate font-semibold text-sem-fg">
                            {selectedMember.name || formatHash(selectedMember.hash)}
                        </span>
                    </div>
                {/if}
                {#if !selectedMember}
                    <div
                        class="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-sem-fg-muted"
                    >
                        <MaterialDesignIcon iconName="account" class="size-10 opacity-40" />
                        {t("relay_chat.host_members_select")}
                    </div>
                {:else}
                    <div class="{RELAY_HOST_DETAIL_HEADER} hidden lg:block">
                        <div class="font-semibold text-sem-fg">
                            {selectedMember.name || formatHash(selectedMember.hash)}
                        </div>
                        <div class="font-mono text-xs text-sem-fg-muted">{formatHash(selectedMember.hash)}</div>
                    </div>
                    <div class="flex shrink-0 flex-wrap items-center gap-2 border-b border-sem-border px-3 py-2">
                        <button
                            type="button"
                            class={BTN_SECONDARY}
                            title={t("relay_chat.kick_member")}
                            onclick={() => moderate(selectedMember!, "kick")}
                        >
                            <MaterialDesignIcon iconName="account-remove" class="size-4" />
                            {t("relay_chat.ctx_kick_user")}
                        </button>
                        <button
                            type="button"
                            class={BTN_SECONDARY}
                            title={t("relay_chat.ban_member")}
                            onclick={() => moderate(selectedMember!, "ban")}
                        >
                            <MaterialDesignIcon iconName="cancel" class="size-4" />
                            {t("relay_chat.ctx_ban_user")}
                        </button>
                        <button
                            type="button"
                            class={BTN_SECONDARY}
                            title={t("relay_chat.ctx_room_ban")}
                            onclick={() => moderate(selectedMember!, "room_ban")}
                        >
                            <MaterialDesignIcon iconName="pound-box" class="size-4" />
                            {t("relay_chat.ctx_room_ban")}
                        </button>
                    </div>
                    <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                        {#if messagesLoading}
                            <div class="py-8 text-center text-sm text-sem-fg-muted">{t("common.loading")}</div>
                        {:else if memberMessages.length === 0}
                            <div class="py-8 text-center text-sm text-sem-fg-muted">
                                {t("relay_chat.host_no_messages")}
                            </div>
                        {:else}
                            <ul class="space-y-2">
                                {#each memberMessages as msg, idx (idx)}
                                    <li class={RELAY_HOST_MESSAGE}>
                                        <div class="flex flex-wrap items-center gap-x-2 text-xs text-sem-fg-muted">
                                            <span>#{msg.room || "?"}</span>
                                            <span>{relativeTime(msg.ts)}</span>
                                        </div>
                                        <div class="mt-1 whitespace-pre-wrap wrap-break-word">{msg.text}</div>
                                    </li>
                                {/each}
                            </ul>
                        {/if}
                    </div>
                {/if}
            </div>
        </div>
    {:else if tab === "status"}
        <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
            {#if statsLoading}
                <div class="py-12 text-center text-sm text-sem-fg-muted">{t("common.loading")}</div>
            {:else}
                <div class="mb-2 text-sm font-semibold text-sem-fg">{t("relay_chat.host_stats_title")}</div>
                <div class="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {#each statCards as card (card.key)}
                        <div class="rounded-lg border border-sem-border bg-sem-surface-raised px-3 py-2">
                            <div class="text-lg font-bold text-sem-fg">{card.value}</div>
                            <div class="text-xs text-sem-fg-muted">{t(`relay_chat.host_stats_${card.key}`)}</div>
                        </div>
                    {/each}
                </div>
                <div class="mb-2 text-sm font-semibold text-sem-fg">{t("relay_chat.host_events_title")}</div>
                {#if statusEvents.length === 0}
                    <div class="py-8 text-center text-sm text-sem-fg-muted">
                        {t("relay_chat.host_events_empty")}
                    </div>
                {:else}
                    <ul class="space-y-1.5">
                        {#each statusEvents as ev, idx (idx)}
                            <li
                                class="flex items-start gap-2 rounded-lg border px-3 py-2 text-xs {isWarningEvent(ev)
                                    ? 'border-amber-500/30 bg-amber-500/10'
                                    : 'border-sem-border bg-sem-surface-raised'}"
                            >
                                <MaterialDesignIcon
                                    iconName={isWarningEvent(ev) ? "alert" : "information-outline"}
                                    class="mt-0.5 size-3.5 shrink-0 {isWarningEvent(ev)
                                        ? 'text-amber-500'
                                        : 'text-sem-fg-muted'}"
                                />
                                <div class="min-w-0 flex-1">
                                    <span class="font-medium text-sem-fg">{eventLabel(ev)}</span>
                                    {#if ev.peer}
                                        <span class="ml-1 font-mono text-sem-fg-muted">{formatHash(ev.peer)}</span>
                                    {/if}
                                    {#if ev.room}
                                        <span class="ml-1 text-sem-fg-muted">#{ev.room}</span>
                                    {/if}
                                    {#if ev.reason}
                                        <span class="ml-1 text-sem-fg-muted">({ev.reason})</span>
                                    {/if}
                                </div>
                                <span class="shrink-0 text-sem-fg-muted">{relativeTime(ev.ts)}</span>
                            </li>
                        {/each}
                    </ul>
                {/if}
            {/if}
        </div>
    {/if}
</div>
