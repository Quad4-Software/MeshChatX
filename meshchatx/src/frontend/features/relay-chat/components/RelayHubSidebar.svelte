<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { hubDisplayName, hubIconName, statusIconColor, formatUnreadBadge } from "../lib/relayFormatters.js";
    import type { RrcHub, RrcRoom } from "../lib/types.js";

    interface Props {
        hubs: RrcHub[];
        selectedHubHash?: string | null;
        selectedRoomName?: string | null;
        collapsed?: boolean;
        expandedHubs?: Record<string, boolean>;
        showUnreadBadges?: boolean;
        onaddhub?: () => void;
        ontogglecollapse?: () => void;
        onselecthub?: (hub: RrcHub) => void;
        onselectroom?: (hub: RrcHub, room: RrcRoom) => void;
        onjoinroom?: (hub: RrcHub) => void;
        onhubcontextmenu?: (e: MouseEvent, hub: RrcHub) => void;
        onroomcontextmenu?: (e: MouseEvent, hub: RrcHub, room: RrcRoom) => void;
        ontogglehubexpanded?: (hubHash: string) => void;
        onreorderhubs?: (fromIdx: number, toIdx: number) => void;
    }

    let {
        hubs = [],
        selectedHubHash = null,
        selectedRoomName = null,
        collapsed = false,
        expandedHubs = {},
        showUnreadBadges = true,
        onaddhub,
        ontogglecollapse,
        onselecthub,
        onselectroom,
        onjoinroom,
        onhubcontextmenu,
        onroomcontextmenu,
        ontogglehubexpanded,
        onreorderhubs,
    }: Props = $props();

    let dragHubIndex = $state<number | null>(null);

    function hubRoomsList(hub: RrcHub): RrcRoom[] {
        if (!hub.rooms) return [];
        if (Array.isArray(hub.rooms)) return hub.rooms;
        return Object.values(hub.rooms);
    }

    function hubTotalUnread(hub: RrcHub): number {
        const rooms = hubRoomsList(hub);
        return rooms.reduce((sum, r) => sum + (r.unread || 0), 0);
    }
</script>

<div
    class="flex flex-col shrink-0 border-r border-sem-border bg-sem-canvas {collapsed
        ? 'w-16 min-w-16 max-w-16'
        : 'w-full md:w-72'}"
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
            class="rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-surface/60 transition-colors"
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
                    onclick={() => onselecthub?.(hub)}
                    oncontextmenu={(e) => {
                        e.preventDefault();
                        onhubcontextmenu?.(e, hub);
                    }}
                >
                    <MaterialDesignIcon iconName={hubIconName(hub)} class="size-6 {statusIconColor(hub.status)}" />
                    {#if showUnreadBadges && hubTotalUnread(hub) > 0}
                        <span
                            class="absolute -top-0.5 -right-0.5 min-w-[14px] rounded-full bg-red-500 px-0.5 text-[9px] font-bold leading-tight text-white"
                        >
                            {formatUnreadBadge(hubTotalUnread(hub))}
                        </span>
                    {/if}
                </button>
            {/each}
        </div>
    {:else}
        <div class="flex-1 overflow-y-auto p-2 space-y-1.5">
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
                    ondragstart={() => {
                        dragHubIndex = hubIndex;
                    }}
                    ondragover={(e) => e.preventDefault()}
                    ondrop={() => {
                        if (dragHubIndex !== null && dragHubIndex !== hubIndex) {
                            onreorderhubs?.(dragHubIndex, hubIndex);
                        }
                        dragHubIndex = null;
                    }}
                    ondragend={() => {
                        dragHubIndex = null;
                    }}
                    oncontextmenu={(e) => {
                        e.preventDefault();
                        onhubcontextmenu?.(e, hub);
                    }}
                    role="region"
                    aria-label={hubDisplayName(hub)}
                >
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors hover:bg-sem-surface/60 cursor-pointer {hub.hub_hash ===
                        selectedHubHash
                            ? 'bg-sem-surface/70 font-semibold'
                            : ''}"
                        onclick={() => {
                            ontogglehubexpanded?.(hub.hub_hash);
                            onselecthub?.(hub);
                        }}
                    >
                        <MaterialDesignIcon
                            iconName={expandedHubs[hub.hub_hash] ? "chevron-down" : "chevron-right"}
                            class="size-4 shrink-0 text-sem-fg-muted"
                        />
                        <MaterialDesignIcon
                            iconName={hubIconName(hub)}
                            class="size-5 shrink-0 {statusIconColor(hub.status)}"
                        />
                        <div class="min-w-0 flex-1">
                            <div class="truncate text-sm">{hubDisplayName(hub)}</div>
                        </div>
                        {#if showUnreadBadges && hubTotalUnread(hub) > 0}
                            <span
                                class="min-w-[16px] rounded-full bg-red-500 px-1 text-[10px] font-bold leading-tight text-white text-center"
                            >
                                {formatUnreadBadge(hubTotalUnread(hub))}
                            </span>
                        {/if}
                    </button>

                    {#if expandedHubs[hub.hub_hash]}
                        <div class="space-y-0.5 pb-2 pl-6 pr-2">
                            <button
                                type="button"
                                class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs text-sem-fg-muted hover:bg-sem-surface/50 hover:text-sem-accent transition-colors cursor-pointer"
                                onclick={() => onjoinroom?.(hub)}
                            >
                                <MaterialDesignIcon iconName="plus" class="size-3.5 shrink-0" />
                                <span>{t("relay_chat.join_room")}</span>
                            </button>

                            {#each hubRoomsList(hub) as room (room.name)}
                                <button
                                    type="button"
                                    class="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs transition-colors cursor-pointer {selectedHubHash ===
                                        hub.hub_hash && selectedRoomName === room.name
                                        ? 'bg-sem-accent/15 text-sem-accent font-semibold'
                                        : 'hover:bg-sem-surface/40 text-sem-fg'}"
                                    onclick={() => onselectroom?.(hub, room)}
                                    oncontextmenu={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        onroomcontextmenu?.(e, hub, room);
                                    }}
                                >
                                    <div class="flex items-center gap-1.5 min-w-0 flex-1">
                                        <MaterialDesignIcon iconName="pound" class="size-3.5 shrink-0 opacity-60" />
                                        <span class="truncate">{room.name}</span>
                                        {#if room.has_key}
                                            <MaterialDesignIcon
                                                iconName="lock"
                                                class="size-3 shrink-0 text-amber-500"
                                            />
                                        {/if}
                                    </div>
                                    {#if (room.unread || 0) > 0}
                                        <span
                                            class="ml-1 min-w-[14px] rounded-full bg-red-500 px-1 text-[9px] font-bold text-white text-center"
                                        >
                                            {formatUnreadBadge(room.unread || 0)}
                                        </span>
                                    {/if}
                                </button>
                            {/each}
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
</div>
