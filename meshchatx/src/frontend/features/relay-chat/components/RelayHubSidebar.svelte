<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        formatUnreadBadge,
        hubDisplayName,
        hubIconName,
        hubTotalUnreadCount,
        isHubConnected,
        orderedKnownRoomNames,
        roomUnreadCount,
        statusIconColor,
        statusLabel,
        statusTextColor,
    } from "../lib/relayFormatters.js";
    import { unjoinedAvailableRooms } from "../../../js/rrcAvailableRooms.js";
    import type { RrcAvailableRoom, RrcHub } from "../lib/types.js";

    interface Props {
        hubs: RrcHub[];
        selectedHubHash?: string | null;
        selectedRoom?: string | null;
        collapsed?: boolean;
        expandedHubs?: Record<string, boolean>;
        availableRoomsExpanded?: Record<string, boolean>;
        availableRoomsRefreshing?: Record<string, boolean>;
        showUnreadBadges?: boolean;
        joinRoomName?: string;
        joinRoomKey?: string;
        formatHash?: (hash: string | null | undefined) => string;
        onaddhub?: () => void;
        ontogglecollapse?: () => void;
        ontogglehub?: (hubHash: string) => void;
        oncollapsedhubclick?: (hub: RrcHub) => void;
        onselectroom?: (hub: RrcHub, roomName: string) => void;
        onjoinroom?: (hub: RrcHub) => void;
        onjoinavailableroom?: (hub: RrcHub, roomName: string) => void;
        onrefreshavailablerooms?: (hub: RrcHub) => void;
        ontoggleavailablerooms?: (hubHash: string) => void;
        onconnecthub?: (hub: RrcHub) => void;
        ondisconnecthub?: (hub: RrcHub) => void;
        onopenhubsettings?: (hub: RrcHub) => void;
        onremovehub?: (hub: RrcHub) => void;
        oncopyhash?: (hash: string) => void;
        onsidebarcontextmenu?: (e: MouseEvent, ctx: { hub?: RrcHub | null; room?: string | null }) => void;
        onreorderhubs?: (fromIdx: number, toIdx: number) => void;
        onreorderrooms?: (hub: RrcHub, fromIdx: number, toIdx: number) => void;
        onpersistroomorder?: (hub: RrcHub) => void;
    }

    let {
        hubs = [],
        selectedHubHash = null,
        selectedRoom = null,
        collapsed = false,
        expandedHubs = {},
        availableRoomsExpanded = {},
        availableRoomsRefreshing = {},
        showUnreadBadges = true,
        joinRoomName = $bindable(""),
        joinRoomKey = $bindable(""),
        formatHash = (h) => h || "-",
        onaddhub,
        ontogglecollapse,
        ontogglehub,
        oncollapsedhubclick,
        onselectroom,
        onjoinroom,
        onjoinavailableroom,
        onrefreshavailablerooms,
        ontoggleavailablerooms,
        onconnecthub,
        ondisconnecthub,
        onopenhubsettings,
        onremovehub,
        oncopyhash,
        onsidebarcontextmenu,
        onreorderhubs,
        onreorderrooms,
        onpersistroomorder,
    }: Props = $props();

    const BTN_PRIMARY =
        "inline-flex items-center justify-center gap-1.5 rounded-lg bg-sem-action-primary px-3 py-2 text-sm font-semibold text-sem-action-primary-text transition hover:bg-sem-action-primary-hover disabled:opacity-50 disabled:cursor-not-allowed";
    const BTN_SECONDARY =
        "inline-flex items-center justify-center gap-1.5 rounded-lg border border-sem-border bg-sem-surface-muted px-3 py-2 text-sm font-medium text-sem-fg transition hover:bg-sem-surface-raised disabled:opacity-50 disabled:cursor-not-allowed";
    const BTN_ICON_SM =
        "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-1.5 text-sem-fg transition hover:bg-sem-surface/60";
    const BTN_DANGER_SM =
        "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-1.5 text-sem-fg transition hover:border-sem-danger hover:text-sem-danger hover:bg-sem-danger/10";

    let dragHubIndex = $state<number | null>(null);
    let dragRoomHubHash = $state<string | null>(null);
    let dragRoomIndex = $state<number | null>(null);

    function isExpanded(hubHash: string): boolean {
        return expandedHubs[hubHash] === true;
    }

    function availableRoomsFor(hub: RrcHub): RrcAvailableRoom[] {
        // Parent computes the diff against joined rooms; fall back to raw list
        // so the sidebar still renders when the callback is absent.
        return unjoinedAvailableRooms(
            hub.available_rooms,
            orderedKnownRoomNames(hub),
            hub.available_keyed_rooms
        ) as RrcAvailableRoom[];
    }

    function isAvailableRoomsExpanded(hubHash: string): boolean {
        return availableRoomsExpanded[hubHash] !== false;
    }

    function isRefreshingAvailableRooms(hubHash: string): boolean {
        return availableRoomsRefreshing[hubHash] === true;
    }

    function onHubDragStart(index: number, event: DragEvent) {
        dragHubIndex = index;
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", String(index));
        }
    }

    function onHubDragOver(index: number) {
        if (dragHubIndex === null || dragHubIndex === index) {
            return;
        }
        onreorderhubs?.(dragHubIndex, index);
        dragHubIndex = index;
    }

    function onHubDrop() {
        dragHubIndex = null;
    }

    function onRoomDragStart(hub: RrcHub, roomIndex: number, event: DragEvent) {
        if (orderedKnownRoomNames(hub).length <= 1) {
            return;
        }
        event.stopPropagation();
        dragRoomHubHash = hub.hub_hash;
        dragRoomIndex = roomIndex;
        dragHubIndex = null;
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", String(roomIndex));
        }
    }

    function onRoomDragOver(hub: RrcHub, roomIndex: number, event: DragEvent) {
        if (dragRoomHubHash !== hub.hub_hash || dragRoomIndex === null) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        if (dragRoomIndex === roomIndex) {
            return;
        }
        onreorderrooms?.(hub, dragRoomIndex, roomIndex);
        dragRoomIndex = roomIndex;
    }

    function onRoomDrop(hub: RrcHub, event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        if (dragRoomHubHash !== hub.hub_hash) {
            onRoomDragEnd();
            return;
        }
        onRoomDragEnd();
        onpersistroomorder?.(hub);
    }

    function onRoomDragEnd() {
        dragRoomHubHash = null;
        dragRoomIndex = null;
    }
</script>

<div
    class="flex flex-col shrink-0 border-r border-sem-border bg-sem-canvas {selectedRoom
        ? 'hidden md:flex'
        : 'flex'} {collapsed ? 'w-16 min-w-16 max-w-16' : 'w-full md:w-72'}"
>
    <div
        class="flex h-10 shrink-0 items-center border-b border-sem-border px-2 {collapsed
            ? 'justify-center'
            : 'justify-between gap-2'}"
    >
        {#if !collapsed}
            <div class="flex items-center gap-2 min-w-0">
                <MaterialDesignIcon iconName="forum" class="size-5 shrink-0 text-sem-accent" />
                <span class="font-semibold truncate">{t("relay_chat.title")}</span>
            </div>
        {/if}
        <button
            type="button"
            class="rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-surface/60 transition-colors cursor-pointer"
            title={collapsed ? t("relay_chat.expand_sidebar") : t("relay_chat.collapse_sidebar")}
            onclick={() => ontogglecollapse?.()}
        >
            <MaterialDesignIcon iconName={collapsed ? "chevron-right" : "chevron-left"} class="size-5" />
        </button>
    </div>

    {#if collapsed}
        <div class="flex flex-1 flex-col items-center gap-1 py-2 px-1">
            <button
                type="button"
                class="rounded-xl p-2 text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-accent cursor-pointer"
                title={t("relay_chat.add_hub")}
                onclick={() => onaddhub?.()}
            >
                <MaterialDesignIcon iconName="plus" class="size-5" />
            </button>
            {#each hubs as hub (hub.hub_hash)}
                <button
                    type="button"
                    class="relative rounded-xl p-2 transition-colors hover:bg-sem-surface/60 cursor-pointer {hub.hub_hash ===
                    selectedHubHash
                        ? 'ring-2 ring-sem-accent'
                        : ''}"
                    title={hubDisplayName(hub)}
                    onclick={() => oncollapsedhubclick?.(hub)}
                    oncontextmenu={(e) => {
                        e.preventDefault();
                        onsidebarcontextmenu?.(e, { hub });
                    }}
                >
                    <MaterialDesignIcon iconName={hubIconName(hub)} class="size-6 {statusIconColor(hub.status)}" />
                    {#if showUnreadBadges && hubTotalUnreadCount(hub) > 0}
                        <span
                            class="absolute -top-0.5 -right-0.5 min-w-[14px] rounded-full bg-red-500 px-0.5 text-[9px] font-bold leading-tight text-white"
                        >
                            {formatUnreadBadge(hubTotalUnreadCount(hub))}
                        </span>
                    {/if}
                </button>
            {/each}
        </div>
    {:else}
        <div
            class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1.5"
            oncontextmenu={(e) => {
                e.preventDefault();
                onsidebarcontextmenu?.(e, {});
            }}
            role="presentation"
        >
            <button
                type="button"
                class="flex w-full items-center gap-2 border-b border-sem-border/60 px-2 py-2.5 text-left text-sm text-sem-fg-muted transition-colors hover:bg-sem-surface/40 hover:text-sem-accent cursor-pointer"
                onclick={() => onaddhub?.()}
            >
                <MaterialDesignIcon iconName="plus" class="size-4 shrink-0" />
                <span class="font-medium">{t("relay_chat.add_hub_card")}</span>
            </button>

            {#each hubs as hub, hubIndex (hub.hub_hash)}
                <div
                    class="border-b border-sem-border/60 {dragHubIndex === hubIndex ? 'opacity-60' : ''}"
                    draggable="true"
                    ondragstart={(e) => {
                        if (dragRoomHubHash) {
                            e.preventDefault();
                            return;
                        }
                        onHubDragStart(hubIndex, e);
                    }}
                    ondragover={(e) => {
                        e.preventDefault();
                        onHubDragOver(hubIndex);
                    }}
                    ondrop={(e) => {
                        e.preventDefault();
                        onHubDrop();
                    }}
                    ondragend={() => {
                        dragHubIndex = null;
                    }}
                    oncontextmenu={(e) => {
                        e.preventDefault();
                        onsidebarcontextmenu?.(e, { hub });
                    }}
                    role="region"
                    aria-label={hubDisplayName(hub)}
                >
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors hover:bg-sem-surface/60 cursor-pointer {hub.hub_hash ===
                        selectedHubHash
                            ? 'bg-sem-surface/70'
                            : ''}"
                        onclick={() => ontogglehub?.(hub.hub_hash)}
                    >
                        <MaterialDesignIcon
                            iconName={isExpanded(hub.hub_hash) ? "chevron-down" : "chevron-right"}
                            class="size-4 shrink-0 text-sem-fg-muted"
                        />
                        <MaterialDesignIcon
                            iconName={hubIconName(hub)}
                            class="size-5 shrink-0 {statusIconColor(hub.status)}"
                        />
                        <div class="min-w-0 flex-1">
                            <div class="truncate font-medium leading-tight">{hubDisplayName(hub)}</div>
                            <div class="truncate text-xs {statusTextColor(hub.status)}">
                                {statusLabel(hub.status)}
                            </div>
                        </div>
                        {#if showUnreadBadges && hubTotalUnreadCount(hub) > 0}
                            <span
                                class="shrink-0 min-w-[1.25rem] rounded-full bg-red-500 px-1.5 py-0.5 text-center text-xs font-bold text-white"
                            >
                                {formatUnreadBadge(hubTotalUnreadCount(hub))}
                            </span>
                        {/if}
                    </button>

                    {#if isExpanded(hub.hub_hash)}
                        <div class="border-t border-sem-border/50 px-2 py-2 space-y-2">
                            <button
                                type="button"
                                class="flex w-full items-center gap-1.5 px-1 font-mono text-xs text-sem-fg-muted hover:text-sem-accent cursor-pointer"
                                title={t("relay_chat.copy_hash")}
                                onclick={(e) => {
                                    e.stopPropagation();
                                    oncopyhash?.(hub.hub_hash);
                                }}
                            >
                                <MaterialDesignIcon iconName="content-copy" class="size-3.5 shrink-0" />
                                <span class="truncate">{formatHash(hub.hub_hash)}</span>
                            </button>
                            <div class="flex items-center gap-1.5">
                                {#if !isHubConnected(hub)}
                                    <button
                                        type="button"
                                        class="{BTN_PRIMARY} flex-1 py-1.5! text-xs!"
                                        onclick={(e) => {
                                            e.stopPropagation();
                                            onconnecthub?.(hub);
                                        }}
                                    >
                                        <MaterialDesignIcon iconName="lan-connect" class="size-4" />
                                        {t("relay_chat.connect")}
                                    </button>
                                {:else}
                                    <button
                                        type="button"
                                        class="{BTN_SECONDARY} flex-1 py-1.5! text-xs!"
                                        onclick={(e) => {
                                            e.stopPropagation();
                                            ondisconnecthub?.(hub);
                                        }}
                                    >
                                        <MaterialDesignIcon iconName="lan-disconnect" class="size-4" />
                                        {t("relay_chat.disconnect")}
                                    </button>
                                {/if}
                                <button
                                    type="button"
                                    class={BTN_ICON_SM}
                                    title={t("relay_chat.settings")}
                                    onclick={(e) => {
                                        e.stopPropagation();
                                        onopenhubsettings?.(hub);
                                    }}
                                >
                                    <MaterialDesignIcon iconName="cog" class="size-4" />
                                </button>
                                <button
                                    type="button"
                                    class={BTN_DANGER_SM}
                                    title={t("relay_chat.remove_hub")}
                                    onclick={(e) => {
                                        e.stopPropagation();
                                        onremovehub?.(hub);
                                    }}
                                >
                                    <MaterialDesignIcon iconName="trash-can-outline" class="size-4" />
                                </button>
                            </div>

                            <ul class="space-y-0">
                                {#each orderedKnownRoomNames(hub) as roomName, roomIndex (roomName)}
                                    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                                    <li
                                        class="flex items-center justify-between gap-2 px-2 py-1 text-sm cursor-pointer transition-colors hover:bg-sem-surface/60 {hub.hub_hash ===
                                            selectedHubHash && roomName === selectedRoom
                                            ? 'bg-sem-action-primary/15 text-sem-accent font-medium'
                                            : ''} {dragRoomHubHash === hub.hub_hash && dragRoomIndex === roomIndex
                                            ? 'opacity-60'
                                            : ''}"
                                        draggable={orderedKnownRoomNames(hub).length > 1}
                                        ondragstart={(e) => onRoomDragStart(hub, roomIndex, e)}
                                        ondragover={(e) => onRoomDragOver(hub, roomIndex, e)}
                                        ondrop={(e) => onRoomDrop(hub, e)}
                                        ondragend={onRoomDragEnd}
                                        onclick={() => onselectroom?.(hub, roomName)}
                                        oncontextmenu={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            onsidebarcontextmenu?.(e, { hub, room: roomName });
                                        }}
                                    >
                                        <span class="flex min-w-0 items-center gap-1.5">
                                            <MaterialDesignIcon iconName="pound" class="size-3.5 shrink-0 opacity-60" />
                                            <span class="truncate">{roomName}</span>
                                        </span>
                                        {#if showUnreadBadges && roomUnreadCount(hub, roomName) > 0}
                                            <span
                                                class="shrink-0 min-w-[1.125rem] rounded-full bg-red-500 px-1 text-center text-[10px] font-bold leading-4 text-white"
                                            >
                                                {formatUnreadBadge(roomUnreadCount(hub, roomName))}
                                            </span>
                                        {/if}
                                    </li>
                                {/each}
                                {#if orderedKnownRoomNames(hub).length === 0 && availableRoomsFor(hub).length === 0}
                                    <li class="px-2.5 py-1 text-xs text-sem-fg-muted">
                                        {t("relay_chat.no_rooms")}
                                    </li>
                                {/if}
                            </ul>

                            {#if isHubConnected(hub) || availableRoomsFor(hub).length > 0}
                                <div class="space-y-0.5">
                                    <div
                                        class="flex w-full items-center gap-1 px-2.5 pt-1 text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted"
                                    >
                                        <button
                                            type="button"
                                            class="flex min-w-0 flex-1 items-center gap-1 text-left transition-colors hover:text-sem-fg cursor-pointer"
                                            onclick={() => ontoggleavailablerooms?.(hub.hub_hash)}
                                        >
                                            <MaterialDesignIcon
                                                iconName={isAvailableRoomsExpanded(hub.hub_hash)
                                                    ? "chevron-down"
                                                    : "chevron-right"}
                                                class="size-3.5 shrink-0"
                                            />
                                            <span class="truncate">{t("relay_chat.available_rooms")}</span>
                                        </button>
                                        <button
                                            type="button"
                                            class="inline-flex size-5 shrink-0 items-center justify-center rounded-md text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-accent disabled:cursor-not-allowed disabled:opacity-40"
                                            disabled={!isHubConnected(hub) || isRefreshingAvailableRooms(hub.hub_hash)}
                                            title={t("relay_chat.refresh_available_rooms")}
                                            onclick={(e) => {
                                                e.stopPropagation();
                                                onrefreshavailablerooms?.(hub);
                                            }}
                                        >
                                            <MaterialDesignIcon
                                                iconName="refresh"
                                                class="size-3.5 {isRefreshingAvailableRooms(hub.hub_hash)
                                                    ? 'animate-spin'
                                                    : ''}"
                                            />
                                        </button>
                                    </div>
                                    {#if isAvailableRoomsExpanded(hub.hub_hash)}
                                        <ul class="space-y-0.5">
                                            {#each availableRoomsFor(hub) as availableRoom (availableRoom.name)}
                                                <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                                                <!-- svelte-ignore a11y_click_events_have_key_events -->
                                                <li
                                                    title={availableRoom.topic ||
                                                        (availableRoom.has_key ? t("relay_chat.host_room_keyed") : "")}
                                                    class="flex items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-sm cursor-pointer text-sem-fg-muted transition-colors hover:bg-sem-surface/60"
                                                    onclick={() => onjoinavailableroom?.(hub, availableRoom.name)}
                                                >
                                                    <span class="flex min-w-0 items-center gap-1.5">
                                                        <MaterialDesignIcon
                                                            iconName={availableRoom.has_key ? "lock" : "pound"}
                                                            class="size-3.5 shrink-0 opacity-40"
                                                        />
                                                        <span class="truncate">{availableRoom.name}</span>
                                                    </span>
                                                    <button
                                                        type="button"
                                                        class="inline-flex size-6 shrink-0 items-center justify-center rounded-md text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-accent"
                                                        title={t("relay_chat.join")}
                                                        onclick={(e) => {
                                                            e.stopPropagation();
                                                            onjoinavailableroom?.(hub, availableRoom.name);
                                                        }}
                                                    >
                                                        <MaterialDesignIcon iconName="plus" class="size-3.5" />
                                                    </button>
                                                </li>
                                            {/each}
                                        </ul>
                                    {/if}
                                </div>
                            {/if}

                            <form
                                class="flex flex-col gap-1"
                                onsubmit={(e) => {
                                    e.preventDefault();
                                    onjoinroom?.(hub);
                                }}
                            >
                                <div class="flex gap-1">
                                    <input
                                        bind:value={joinRoomName}
                                        type="text"
                                        data-relay-join-input
                                        placeholder={t("relay_chat.join_room_placeholder")}
                                        class="min-w-0 flex-1 border border-sem-border bg-sem-canvas px-2 py-1 text-xs text-sem-fg outline-hidden focus:border-sem-accent focus:ring-1 focus:ring-sem-accent/30"
                                    />
                                    <button
                                        type="submit"
                                        class="inline-flex size-7 shrink-0 items-center justify-center rounded-md text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-accent"
                                        title={t("relay_chat.join_room")}
                                    >
                                        <MaterialDesignIcon iconName="plus" class="size-4" />
                                    </button>
                                </div>
                                <input
                                    bind:value={joinRoomKey}
                                    type="password"
                                    placeholder={t("relay_chat.join_room_key_placeholder")}
                                    autocomplete="off"
                                    class="w-full border border-sem-border bg-sem-canvas px-2 py-1 text-xs text-sem-fg outline-hidden focus:border-sem-accent focus:ring-1 focus:ring-sem-accent/30"
                                />
                            </form>
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
</div>
