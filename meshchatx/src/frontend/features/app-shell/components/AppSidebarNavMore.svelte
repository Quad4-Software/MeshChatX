<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import AppSidebarNavItem from "./AppSidebarNavItem.svelte";
    import type { NavItem, NavReorderPayload } from "../lib/navTypes.js";
    import type { NavEditHoldController } from "../lib/navEditHold.js";

    interface Props {
        moreNavItems?: NavItem[];
        isCollapsed?: boolean;
        isEditing?: boolean;
        isShowingMoreNav?: boolean;
        activeRouteName?: string;
        unreadConversationsCount?: number;
        relayChatUnreadCount?: number;
        missedCallsCount?: number;
        controller: NavEditHoldController;
        onmoretoggle?: () => void;
        onmoredrop?: () => void;
        onnavreorder?: (payload: NavReorderPayload) => void;
        onitemdragstart?: (itemId: string, event: DragEvent) => void;
        onitemdragover?: (itemId: string, event: DragEvent) => void;
        onitemdrop?: (itemId: string, event: DragEvent) => void;
    }

    let {
        moreNavItems = [],
        isCollapsed = false,
        isEditing = false,
        isShowingMoreNav = false,
        activeRouteName = "",
        unreadConversationsCount = 0,
        relayChatUnreadCount = 0,
        missedCallsCount = 0,
        controller,
        onmoretoggle,
        onmoredrop,
        onnavreorder,
        onitemdragstart,
        onitemdragover,
        onitemdrop,
    }: Props = $props();
</script>

{#if moreNavItems.length > 0 || isEditing}
    <div class="mt-1 border-t border-sem-border {controller.dragOverKey === 'more' ? 'bg-sem-surface-muted' : ''}">
        <button
            type="button"
            class="flex w-full items-center gap-3 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-100 text-sem-fg dark:hover:bg-zinc-800 transition-colors {isCollapsed
                ? 'justify-center px-0'
                : 'px-4'}"
            data-testid="sidebar-more-toggle"
            onpointerdown={(e) => controller.onPointerDown(e)}
            onpointermove={(e) => controller.onPointerMove(e)}
            onpointerup={() => controller.onPointerUp()}
            onpointercancel={() => controller.onPointerUp()}
            onclickcapture={(e) => controller.onClickCapture(e)}
            oncontextmenu={(e) => controller.onContextMenu(e)}
            onclick={() => onmoretoggle?.()}
            ondragover={(e) => {
                e.preventDefault();
                controller.setNavDragOver("more", e);
            }}
            ondrop={(e) => {
                e.preventDefault();
                onmoredrop?.();
            }}
        >
            <MaterialDesignIcon iconName="dots-horizontal" class="size-6 shrink-0" />
            {#if !isCollapsed}
                <span class="flex-1 text-left">{t("app.nav_more")}</span>
                <MaterialDesignIcon
                    iconName={isShowingMoreNav ? "chevron-up" : "chevron-down"}
                    class="size-5 shrink-0 text-gray-400"
                />
            {/if}
        </button>
        {#if isShowingMoreNav && !isCollapsed}
            <ul class="py-1 pr-2 space-y-1">
                {#each moreNavItems as item (item.id)}
                    <AppSidebarNavItem
                        {item}
                        isCollapsed={false}
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
        {/if}
    </div>
{/if}
