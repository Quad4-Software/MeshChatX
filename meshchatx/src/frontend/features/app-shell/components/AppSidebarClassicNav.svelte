<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy, untrack } from "svelte";
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import SidebarLink from "./SidebarLink.svelte";
    import { NavEditHoldController } from "../lib/navEditHold.js";

    interface NavBadge {
        source?: string;
        pill?: boolean;
        cap?: number;
    }

    interface NavItem {
        id: string;
        route: { name?: string; path?: string; params?: Record<string, unknown>; query?: Record<string, unknown> };
        icon: string;
        label?: string;
        labelKey?: string;
        badge?: NavBadge;
    }

    interface Props {
        navItems: NavItem[];
        isCollapsed?: boolean;
        isEditing?: boolean;
        unreadConversationsCount?: number;
        relayChatUnreadCount?: number;
        missedCallsCount?: number;
        activeRouteName?: string;

        oneditstart?: () => void;
        onnavreorder?: (payload: unknown) => void;
    }

    let {
        navItems = [],
        isCollapsed = false,
        isEditing = false,
        unreadConversationsCount = 0,
        relayChatUnreadCount = 0,
        missedCallsCount = 0,
        activeRouteName = "",

        oneditstart,
        onnavreorder,
    }: Props = $props();

    let dragVersion = $state(0);

    const controller = new NavEditHoldController(
        () => isCollapsed,
        () => isEditing,
        () => oneditstart?.(),
        () => {
            dragVersion++;
        }
    );

    onDestroy(() => {
        controller.reset();
    });

    $effect(() => {
        if (!isEditing || isCollapsed) {
            untrack(() => {
                controller.reset();
            });
        }
    });

    function getNavBadgeCount(item: NavItem): number {
        if (!item.badge?.source) {
            return 0;
        }
        if (item.badge.source === "unreadConversationsCount") {
            return unreadConversationsCount;
        }
        if (item.badge.source === "relayChatUnreadCount") {
            return relayChatUnreadCount;
        }
        if (item.badge.source === "missedCallsCount") {
            return missedCallsCount;
        }
        return 0;
    }

    function formatNavBadgeCount(item: NavItem): string {
        const count = getNavBadgeCount(item);
        const cap = item.badge?.cap;
        if (cap != null && count > cap) {
            return `${cap}+`;
        }
        return String(count);
    }

    function onItemDragStart(itemId: string, event: DragEvent) {
        controller.beginNavDrag("item", itemId, event);
    }

    function onItemDragOver(itemId: string, event: DragEvent) {
        controller.setNavDragOver(`item:${itemId}`, event);
    }

    function onItemDrop(itemId: string, event: DragEvent) {
        if (controller.draggingKind === "item" && controller.draggingId && controller.draggingId !== itemId) {
            onnavreorder?.({
                kind: "item",
                itemId: controller.draggingId,
                target: { type: "item", id: itemId, position: controller.dropPosition(event) },
            });
        }
        controller.clearNavDrag();
    }
</script>

<span class="hidden" data-drag-version={dragVersion}></span>

<div class="flex-1 overflow-y-auto {isEditing ? 'select-none' : ''}" data-testid="sidebar-classic-nav">
    <ul class="py-3 space-y-1 {isCollapsed ? 'px-0' : 'pr-2'}">
        {#each navItems as item (item.id)}
            <li
                class="flex items-center {isCollapsed ? 'justify-center' : ''} {isEditing &&
                controller.draggingId === item.id &&
                controller.draggingKind === 'item'
                    ? 'opacity-50'
                    : ''} {isEditing && controller.dragOverKey === `item:${item.id}`
                    ? 'ring-1 ring-sem-accent rounded-r-full'
                    : ''}"
                data-testid="sidebar-nav-item"
                data-nav-item-id={item.id}
                draggable={isEditing ? true : undefined}
                onpointerdown={(e) => controller.onPointerDown(e)}
                onpointermove={(e) => controller.onPointerMove(e)}
                onpointerup={() => controller.onPointerUp()}
                onpointercancel={() => controller.onPointerUp()}
                onclickcapture={(e) => controller.onClickCapture(e)}
                oncontextmenu={(e) => controller.onContextMenu(e)}
                ondragstart={(e) => onItemDragStart(item.id, e)}
                ondragover={(e) => {
                    e.preventDefault();
                    onItemDragOver(item.id, e);
                }}
                ondrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onItemDrop(item.id, e);
                }}
                ondragend={() => controller.clearNavDrag()}
            >
                {#if isEditing && !isCollapsed}
                    <MaterialDesignIcon iconName="drag-vertical" class="ml-1 size-4 shrink-0 opacity-50" />
                {/if}
                <SidebarLink
                    class="min-w-0 flex-1"
                    to={item.route}
                    {isCollapsed}
                    editMode={isEditing}
                    {activeRouteName}
                >
                    {#snippet icon()}
                        <span class="relative inline-flex shrink-0">
                            <MaterialDesignIcon iconName={item.icon} class="w-6 h-6 text-sem-fg-secondary" />
                            {#if isCollapsed && getNavBadgeCount(item) > 0 && item.badge?.pill}
                                <span
                                    class="absolute -right-2 -top-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white"
                                >
                                    {formatNavBadgeCount(item)}
                                </span>
                            {/if}
                        </span>
                    {/snippet}
                    {#snippet text()}
                        <span>{item.label || (item.labelKey ? t(item.labelKey) : "")}</span>
                        {#if getNavBadgeCount(item) > 0 && !item.badge?.pill}
                            <span class="ml-auto mr-2">
                                {getNavBadgeCount(item)}
                            </span>
                        {:else if !isCollapsed && getNavBadgeCount(item) > 0 && item.badge?.pill}
                            <span
                                class="ml-auto mr-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white"
                            >
                                {formatNavBadgeCount(item)}
                            </span>
                        {/if}
                    {/snippet}
                </SidebarLink>
                {#if isEditing && !isCollapsed}
                    <div class="flex shrink-0 flex-col pr-1">
                        <button
                            type="button"
                            class="p-0.5 text-gray-400 hover:text-gray-700 hover:text-sem-fg"
                            title={t("app.nav_move_up")}
                            aria-label={t("app.nav_move_up")}
                            onclick={(e) => {
                                e.stopPropagation();
                                onnavreorder?.({ kind: "item-offset", itemId: item.id, delta: -1 });
                            }}
                        >
                            <MaterialDesignIcon iconName="chevron-up" class="size-4" />
                        </button>
                        <button
                            type="button"
                            class="p-0.5 text-gray-400 hover:text-gray-700 hover:text-sem-fg"
                            title={t("app.nav_move_down")}
                            aria-label={t("app.nav_move_down")}
                            onclick={(e) => {
                                e.stopPropagation();
                                onnavreorder?.({ kind: "item-offset", itemId: item.id, delta: 1 });
                            }}
                        >
                            <MaterialDesignIcon iconName="chevron-down" class="size-4" />
                        </button>
                    </div>
                {/if}
            </li>
        {/each}
    </ul>
</div>
