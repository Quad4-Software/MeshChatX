<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy, untrack } from "svelte";
    import AppSidebarNavGroup from "./AppSidebarNavGroup.svelte";
    import AppSidebarNavMore from "./AppSidebarNavMore.svelte";
    import { NavEditHoldController } from "../lib/navEditHold.js";
    import type { NavGroup, NavItem, NavReorderPayload } from "../lib/navTypes.js";

    interface Props {
        primaryNavGroups: NavGroup[];
        moreNavItems?: NavItem[];
        isCollapsed?: boolean;
        isEditing?: boolean;
        isShowingMoreNav?: boolean;
        unreadConversationsCount?: number;
        relayChatUnreadCount?: number;
        missedCallsCount?: number;
        activeRouteName?: string;

        onmoretoggle?: () => void;
        oneditstart?: () => void;
        onnavreorder?: (payload: NavReorderPayload) => void;
    }

    let {
        primaryNavGroups = [],
        moreNavItems = [],
        isCollapsed = false,
        isEditing = false,
        isShowingMoreNav = false,
        unreadConversationsCount = 0,
        relayChatUnreadCount = 0,
        missedCallsCount = 0,
        activeRouteName = "",

        onmoretoggle,
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

    function onItemDragStart(itemId: string, event: DragEvent) {
        controller.beginNavDrag("item", itemId, event);
    }

    function onGroupDragStart(groupId: string, event: DragEvent) {
        controller.beginNavDrag("group", groupId, event);
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
        } else if (controller.draggingKind === "group" && controller.draggingId) {
            const group = primaryNavGroups.find((entry) => entry.items.some((item) => item.id === itemId));
            if (group && group.id !== controller.draggingId) {
                onnavreorder?.({
                    kind: "group",
                    groupId: controller.draggingId,
                    beforeGroupId: group.id,
                });
            }
        }
        controller.clearNavDrag();
    }

    function onGroupHeaderDrop(groupId: string) {
        if (controller.draggingKind === "item" && controller.draggingId) {
            onnavreorder?.({
                kind: "item",
                itemId: controller.draggingId,
                target: { type: "group-start", id: groupId },
            });
        } else if (controller.draggingKind === "group" && controller.draggingId && controller.draggingId !== groupId) {
            onnavreorder?.({
                kind: "group",
                groupId: controller.draggingId,
                beforeGroupId: groupId,
            });
        }
        controller.clearNavDrag();
    }

    function onGroupListDrop(groupId: string) {
        if (controller.draggingKind === "item" && controller.draggingId) {
            onnavreorder?.({
                kind: "item",
                itemId: controller.draggingId,
                target: { type: "group-end", id: groupId },
            });
        }
        controller.clearNavDrag();
    }

    function onMoreDrop() {
        if (controller.draggingKind === "item" && controller.draggingId) {
            onnavreorder?.({
                kind: "item",
                itemId: controller.draggingId,
                target: { type: "more-start" },
            });
        }
        controller.clearNavDrag();
    }
</script>

<span class="hidden" data-drag-version={dragVersion}></span>

<div class="flex-1 overflow-y-auto {isEditing ? 'select-none' : ''}" data-testid="sidebar-nav">
    {#each primaryNavGroups as group (group.id)}
        <AppSidebarNavGroup
            {group}
            {isCollapsed}
            {isEditing}
            {activeRouteName}
            {unreadConversationsCount}
            {relayChatUnreadCount}
            {missedCallsCount}
            {controller}
            {onnavreorder}
            ongroupdragstart={onGroupDragStart}
            ongroupheaderdrop={onGroupHeaderDrop}
            ongrouplistdrop={onGroupListDrop}
            onitemdragstart={onItemDragStart}
            onitemdragover={onItemDragOver}
            onitemdrop={onItemDrop}
        />
    {/each}

    <AppSidebarNavMore
        {moreNavItems}
        {isCollapsed}
        {isEditing}
        {isShowingMoreNav}
        {activeRouteName}
        {unreadConversationsCount}
        {relayChatUnreadCount}
        {missedCallsCount}
        {controller}
        {onmoretoggle}
        onmoredrop={onMoreDrop}
        {onnavreorder}
        onitemdragstart={onItemDragStart}
        onitemdragover={onItemDragOver}
        onitemdrop={onItemDrop}
    />
</div>
