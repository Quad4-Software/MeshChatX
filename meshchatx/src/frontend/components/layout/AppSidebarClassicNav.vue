<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex-1 overflow-y-auto" :class="isEditing ? 'select-none' : ''" data-testid="sidebar-classic-nav">
        <ul class="py-3 pr-2 space-y-1">
            <li
                v-for="item in navItems"
                :key="item.id"
                class="flex items-center"
                :class="[
                    isEditing && draggingId === item.id && draggingKind === 'item' ? 'opacity-50' : '',
                    isEditing && dragOverKey === `item:${item.id}`
                        ? 'ring-1 ring-blue-400 dark:ring-blue-500 rounded-r-full'
                        : '',
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
                <SidebarLink class="min-w-0 flex-1" :to="item.route" :is-collapsed="isCollapsed" :edit-mode="isEditing">
                    <template #icon>
                        <span class="relative inline-flex shrink-0">
                            <MaterialDesignIcon :icon-name="item.icon" class="w-6 h-6 text-gray-700 dark:text-white" />
                            <span
                                v-if="isCollapsed && getNavBadgeCount(item) > 0 && item.badge?.pill"
                                class="absolute -right-2 -top-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white"
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
                            class="ml-auto mr-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white"
                        >
                            {{ formatNavBadgeCount(item) }}
                        </span>
                    </template>
                </SidebarLink>
                <div v-if="isEditing && !isCollapsed" class="flex shrink-0 flex-col pr-1">
                    <button
                        type="button"
                        class="p-0.5 text-gray-400 hover:text-gray-700 dark:hover:text-zinc-200"
                        :title="$t('app.nav_move_up')"
                        :aria-label="$t('app.nav_move_up')"
                        @click.stop="$emit('nav-reorder', { kind: 'item-offset', itemId: item.id, delta: -1 })"
                    >
                        <MaterialDesignIcon icon-name="chevron-up" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="p-0.5 text-gray-400 hover:text-gray-700 dark:hover:text-zinc-200"
                        :title="$t('app.nav_move_down')"
                        :aria-label="$t('app.nav_move_down')"
                        @click.stop="$emit('nav-reorder', { kind: 'item-offset', itemId: item.id, delta: 1 })"
                    >
                        <MaterialDesignIcon icon-name="chevron-down" class="size-4" />
                    </button>
                </div>
            </li>
        </ul>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SidebarLink from "../SidebarLink.vue";
import { navEditHoldMixin } from "../../js/appSidebarNavEditHold.js";

export default {
    name: "AppSidebarClassicNav",
    components: {
        MaterialDesignIcon,
        SidebarLink,
    },
    mixins: [navEditHoldMixin],
    props: {
        navItems: {
            type: Array,
            required: true,
        },
        isCollapsed: {
            type: Boolean,
            default: false,
        },
        isEditing: {
            type: Boolean,
            default: false,
        },
        unreadConversationsCount: {
            type: Number,
            default: 0,
        },
        relayChatUnreadCount: {
            type: Number,
            default: 0,
        },
        missedCallsCount: {
            type: Number,
            default: 0,
        },
    },
    emits: ["edit-start", "nav-reorder"],
    methods: {
        getNavBadgeCount(item) {
            if (!item.badge?.source) {
                return 0;
            }
            if (item.badge.source === "unreadConversationsCount") {
                return this.unreadConversationsCount;
            }
            if (item.badge.source === "relayChatUnreadCount") {
                return this.relayChatUnreadCount;
            }
            if (item.badge.source === "missedCallsCount") {
                return this.missedCallsCount;
            }
            return 0;
        },
        formatNavBadgeCount(item) {
            const count = this.getNavBadgeCount(item);
            const cap = item.badge?.cap;
            if (cap != null && count > cap) {
                return `${cap}+`;
            }
            return String(count);
        },
        onItemDragStart(itemId, event) {
            this.beginNavDrag("item", itemId, event);
        },
        onItemDragOver(itemId, event) {
            this.setNavDragOver(`item:${itemId}`, event);
        },
        onItemDrop(itemId, event) {
            if (this.draggingKind === "item" && this.draggingId && this.draggingId !== itemId) {
                this.$emit("nav-reorder", {
                    kind: "item",
                    itemId: this.draggingId,
                    target: { type: "item", id: itemId, position: this.dropPosition(event) },
                });
            }
            this.clearNavDrag();
        },
    },
};
</script>
