<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import SidebarLink from "./SidebarLink.svelte";
    import type { NavItem, NavReorderPayload } from "../lib/navTypes.js";
    import type { NavEditHoldController } from "../lib/navEditHold.js";

    interface Props {
        item: NavItem;
        isCollapsed?: boolean;
        isEditing?: boolean;
        activeRouteName?: string;
        unreadConversationsCount?: number;
        relayChatUnreadCount?: number;
        missedCallsCount?: number;
        controller: NavEditHoldController;
        onnavreorder?: (payload: NavReorderPayload) => void;
        ondragstart?: (itemId: string, event: DragEvent) => void;
        ondragover?: (itemId: string, event: DragEvent) => void;
        ondrop?: (itemId: string, event: DragEvent) => void;
    }

    let {
        item,
        isCollapsed = false,
        isEditing = false,
        activeRouteName = "",
        unreadConversationsCount = 0,
        relayChatUnreadCount = 0,
        missedCallsCount = 0,
        controller,
        onnavreorder,
        ondragstart,
        ondragover,
        ondrop,
    }: Props = $props();

    function getNavBadgeCount(navItem: NavItem): number {
        if (!navItem.badge?.source) {
            return 0;
        }
        if (navItem.badge.source === "unreadConversationsCount") {
            return unreadConversationsCount;
        }
        if (navItem.badge.source === "relayChatUnreadCount") {
            return relayChatUnreadCount;
        }
        if (navItem.badge.source === "missedCallsCount") {
            return missedCallsCount;
        }
        return 0;
    }

    function formatNavBadgeCount(navItem: NavItem): string {
        const count = getNavBadgeCount(navItem);
        const cap = navItem.badge?.cap;
        if (cap != null && count > cap) {
            return `${cap}+`;
        }
        return String(count);
    }
</script>

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
    ondragstart={(e) => ondragstart?.(item.id, e)}
    ondragover={(e) => {
        e.preventDefault();
        ondragover?.(item.id, e);
    }}
    ondrop={(e) => {
        e.preventDefault();
        e.stopPropagation();
        ondrop?.(item.id, e);
    }}
    ondragend={() => controller.clearNavDrag()}
>
    {#if isEditing && !isCollapsed}
        <MaterialDesignIcon iconName="drag-vertical" class="ml-1 size-4 shrink-0 opacity-50" />
    {/if}
    <SidebarLink class="min-w-0 flex-1" to={item.route} {isCollapsed} editMode={isEditing} {activeRouteName}>
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
