<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <nav
        class="flex-1 overflow-y-auto"
        :class="isEditing ? 'select-none' : ''"
        aria-label="Primary"
        data-testid="sidebar-classic-nav"
    >
        <ul class="py-3 space-y-1" :class="isCollapsed ? 'px-0' : 'pr-2'">
            <li
                v-for="item in navItems"
                :key="item.id"
                class="flex items-center"
                :class="[
                    isCollapsed ? 'justify-center' : '',
                    isEditing && draggingId === item.id && draggingKind === 'item' ? 'opacity-50' : '',
                    isEditing && dragOverKey === `item:${item.id}` ? 'ring-1 ring-sem-accent rounded-r-full' : '',
                ]"
                data-testid="sidebar-nav-item"
                :data-nav-item-id="item.id"
                :draggable="isEditing ? true : undefined"
                @pointerdown="onNavHoldPointerDown"
                @pointermove="onNavHoldPointerMove"
                @pointerup="onNavHoldPointerUp"
                @pointercancel="onNavHoldPointerUp"
                @click.capture="onNavHoldClickCapture"
                @contextmenu="onNavHoldContextMenu"
                @dragstart="onItemDragStart(item.id, $event)"
                @dragover.prevent="onItemDragOver(item.id, $event)"
                @drop.prevent.stop="onItemDrop(item.id, $event)"
                @dragend="clearNavDrag"
            >
                <MaterialDesignIcon
                    v-if="isEditing && !isCollapsed"
                    icon-name="drag-vertical"
                    class="ml-1 size-4 shrink-0 opacity-50"
                />
                <SidebarLink
                    class="min-w-0 flex-1"
                    :to="item.route"
                    :is-collapsed="isCollapsed"
                    :edit-mode="isEditing"
                    <!-- eslint-disable-next-line vue/attribute-hyphenation -- camelCase required: vue-tsc does not normalize aria-label to the ariaLabel prop -->
                    :ariaLabel="item.label || $t(item.labelKey)"
                >
                    <template #icon>
                        <span class="relative inline-flex shrink-0">
                            <MaterialDesignIcon :icon-name="item.icon" class="w-6 h-6 text-sem-fg-secondary" />
                            <span
                                v-if="isCollapsed && getNavBadgeCount(item) > 0 && item.badge?.pill"
                                class="absolute -right-2 -top-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-sem-danger px-1 text-[10px] font-bold leading-none text-white"
                            >
                                {{ formatNavBadgeCount(item) }}
                            </span>
                        </span>
                    </template>
                    <template #text>
                        <span>{{ item.label || $t(item.labelKey) }}</span>
                        <span v-if="getNavBadgeCount(item) > 0 && !item.badge?.pill" class="ml-auto mr-2">
                            {{ getNavBadgeCount(item) }}
                        </span>
                        <span
                            v-else-if="!isCollapsed && getNavBadgeCount(item) > 0 && item.badge?.pill"
                            class="ml-auto mr-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-sem-danger px-1 text-[10px] font-bold leading-none text-white"
                        >
                            {{ formatNavBadgeCount(item) }}
                        </span>
                    </template>
                </SidebarLink>
                <div v-if="isEditing && !isCollapsed" class="flex shrink-0 flex-col pr-1">
                    <button
                        type="button"
                        class="p-0.5 text-sem-fg-muted hover:text-sem-fg hover:text-sem-fg"
                        :title="$t('app.nav_move_up')"
                        :aria-label="$t('app.nav_move_up')"
                        @click.stop="emit('nav-reorder', { kind: 'item-offset', itemId: item.id, delta: -1 })"
                    >
                        <MaterialDesignIcon icon-name="chevron-up" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="p-0.5 text-sem-fg-muted hover:text-sem-fg hover:text-sem-fg"
                        :title="$t('app.nav_move_down')"
                        :aria-label="$t('app.nav_move_down')"
                        @click.stop="emit('nav-reorder', { kind: 'item-offset', itemId: item.id, delta: 1 })"
                    >
                        <MaterialDesignIcon icon-name="chevron-down" class="size-4" />
                    </button>
                </div>
            </li>
        </ul>
    </nav>
</template>

<script setup lang="ts">
import { toRef } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SidebarLink from "../SidebarLink.vue";
import { useNavEditHold } from "../../js/useNavEditHold";

const props = withDefaults(
    defineProps<{
        navItems: any[];
        isCollapsed?: boolean;
        isEditing?: boolean;
        unreadConversationsCount?: number;
        relayChatUnreadCount?: number;
        missedCallsCount?: number;
    }>(),
    {
        isCollapsed: false,
        isEditing: false,
        unreadConversationsCount: 0,
        relayChatUnreadCount: 0,
        missedCallsCount: 0,
    }
);

const emit = defineEmits<{
    "edit-start": [];
    "nav-reorder": [payload: Record<string, any>];
}>();

const {
    draggingKind,
    draggingId,
    dragOverKey,
    clearNavDrag,
    onNavHoldPointerDown,
    onNavHoldPointerMove,
    onNavHoldPointerUp,
    onNavHoldClickCapture,
    onNavHoldContextMenu,
    beginNavDrag,
    setNavDragOver,
    dropPosition,
} = useNavEditHold({
    isEditing: toRef(props, "isEditing"),
    isCollapsed: toRef(props, "isCollapsed"),
    onEditStart: () => emit("edit-start"),
});

function getNavBadgeCount(item: any) {
    if (!item.badge?.source) {
        return 0;
    }
    if (item.badge.source === "unreadConversationsCount") {
        return props.unreadConversationsCount;
    }
    if (item.badge.source === "relayChatUnreadCount") {
        return props.relayChatUnreadCount;
    }
    if (item.badge.source === "missedCallsCount") {
        return props.missedCallsCount;
    }
    return 0;
}

function formatNavBadgeCount(item: any) {
    const count = getNavBadgeCount(item);
    const cap = item.badge?.cap;
    if (cap != null && count > cap) {
        return `${cap}+`;
    }
    return String(count);
}

function onItemDragStart(itemId: string, event: DragEvent) {
    beginNavDrag("item", itemId, event);
}

function onItemDragOver(itemId: string, event: DragEvent) {
    setNavDragOver(`item:${itemId}`, event);
}

function onItemDrop(itemId: string, event: DragEvent) {
    if (draggingKind.value === "item" && draggingId.value && draggingId.value !== itemId) {
        emit("nav-reorder", {
            kind: "item",
            itemId: draggingId.value,
            target: { type: "item", id: itemId, position: dropPosition(event) },
        });
    }
    clearNavDrag();
}
</script>
