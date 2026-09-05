<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import AppSidebarNavItem from "./AppSidebarNavItem.svelte";
    import type { NavGroup, NavReorderPayload } from "../lib/navTypes.js";
    import type { NavEditHoldController } from "../lib/navEditHold.js";

    interface Props {
        group: NavGroup;
        isCollapsed?: boolean;
        isEditing?: boolean;
        activeRouteName?: string;
        unreadConversationsCount?: number;
        relayChatUnreadCount?: number;
        missedCallsCount?: number;
        controller: NavEditHoldController;
        onnavreorder?: (payload: NavReorderPayload) => void;
        ongroupdragstart?: (groupId: string, event: DragEvent) => void;
        ongroupheaderdrop?: (groupId: string) => void;
        ongrouplistdrop?: (groupId: string) => void;
        onitemdragstart?: (itemId: string, event: DragEvent) => void;
        onitemdragover?: (itemId: string, event: DragEvent) => void;
        onitemdrop?: (itemId: string, event: DragEvent) => void;
    }

    let {
        group,
        isCollapsed = false,
        isEditing = false,
        activeRouteName = "",
        unreadConversationsCount = 0,
        relayChatUnreadCount = 0,
        missedCallsCount = 0,
        controller,
        onnavreorder,
        ongroupdragstart,
        ongroupheaderdrop,
        ongrouplistdrop,
        onitemdragstart,
        onitemdragover,
        onitemdrop,
    }: Props = $props();
</script>

{#if !isCollapsed}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="px-4 pt-2 pb-1 text-[10px] font-bold uppercase tracking-widest text-sem-fg-muted {isEditing
            ? 'flex cursor-grab items-center gap-1'
            : ''} {controller.dragOverKey === `group:${group.id}` ? 'bg-sem-surface-muted' : ''}"
        data-testid="sidebar-nav-group"
        data-group-id={group.id}
        draggable={isEditing ? true : undefined}
        onpointerdown={(e) => controller.onPointerDown(e)}
        onpointermove={(e) => controller.onPointerMove(e)}
        onpointerup={() => controller.onPointerUp()}
        onpointercancel={() => controller.onPointerUp()}
        onclickcapture={(e) => controller.onClickCapture(e)}
        oncontextmenu={(e) => controller.onContextMenu(e)}
        ondragstart={(e) => ongroupdragstart?.(group.id, e)}
        ondragover={(e) => {
            e.preventDefault();
            controller.setNavDragOver(`group:${group.id}`, e);
        }}
        ondrop={(e) => {
            e.preventDefault();
            ongroupheaderdrop?.(group.id);
        }}
        ondragend={() => controller.clearNavDrag()}
    >
        {#if isEditing}
            <MaterialDesignIcon iconName="drag-vertical" class="size-4 shrink-0 opacity-50" />
        {/if}
        <span class="min-w-0 flex-1 truncate">{t(`app.nav_group.${group.id}`)}</span>
        {#if isEditing}
            <button
                type="button"
                class="p-0.5 text-gray-400 hover:text-gray-700 hover:text-sem-fg"
                title={t("app.nav_move_up")}
                aria-label={t("app.nav_move_up")}
                onclick={(e) => {
                    e.stopPropagation();
                    onnavreorder?.({ kind: "group-offset", groupId: group.id, delta: -1 });
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
                    onnavreorder?.({ kind: "group-offset", groupId: group.id, delta: 1 });
                }}
            >
                <MaterialDesignIcon iconName="chevron-down" class="size-4" />
            </button>
        {/if}
    </div>
{/if}

<ul
    class="py-1 space-y-1 {isCollapsed ? 'px-0' : 'pr-2'}"
    ondragover={(e) => {
        e.preventDefault();
        controller.setNavDragOver(`group-end:${group.id}`, e);
    }}
    ondrop={(e) => {
        e.preventDefault();
        ongrouplistdrop?.(group.id);
    }}
>
    {#each group.items as item (item.id)}
        <AppSidebarNavItem
            {item}
            {isCollapsed}
            {isEditing}
            {activeRouteName}
            {unreadConversationsCount}
            {relayChatUnreadCount}
            {missedCallsCount}
            {controller}
            {onnavreorder}
            ondragstart={onitemdragstart}
            ondragover={onitemdragover}
            ondrop={onitemdrop}
        />
    {/each}
</ul>
