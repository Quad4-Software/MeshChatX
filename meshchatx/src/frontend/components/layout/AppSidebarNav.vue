<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex-1 overflow-y-auto" :class="isEditing ? 'select-none' : ''" data-testid="sidebar-nav">
        <template v-for="group in primaryNavGroups" :key="group.id">
            <div
                v-if="!isCollapsed"
                class="px-4 pt-2 pb-1 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500"
                :class="[
                    isEditing ? 'flex cursor-grab items-center gap-1' : '',
                    dragOverKey === `group:${group.id}` ? 'bg-blue-50 dark:bg-blue-900/20' : '',
                ]"
                data-testid="sidebar-nav-group"
                :data-group-id="group.id"
                :draggable="isEditing ? true : undefined"
                @pointerdown="onNavHoldPointerDown"
                @pointermove="onNavHoldPointerMove"
                @pointerup="onNavHoldPointerUp"
                @pointercancel="onNavHoldPointerUp"
                @click.capture="onNavHoldClickCapture"
                @contextmenu="onNavHoldContextMenu"
                @dragstart="onGroupDragStart(group.id, $event)"
                @dragover.prevent="setNavDragOver(`group:${group.id}`, $event)"
                @drop.prevent="onGroupHeaderDrop(group.id)"
                @dragend="clearNavDrag"
            >
                <MaterialDesignIcon v-if="isEditing" icon-name="drag-vertical" class="size-4 shrink-0 opacity-50" />
                <span class="min-w-0 flex-1 truncate">{{ $t(`app.nav_group.${group.id}`) }}</span>
                <template v-if="isEditing">
                    <button
                        type="button"
                        class="p-0.5 text-gray-400 hover:text-gray-700 dark:hover:text-zinc-200"
                        :title="$t('app.nav_move_up')"
                        :aria-label="$t('app.nav_move_up')"
                        @click.stop="$emit('nav-reorder', { kind: 'group-offset', groupId: group.id, delta: -1 })"
                    >
                        <MaterialDesignIcon icon-name="chevron-up" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="p-0.5 text-gray-400 hover:text-gray-700 dark:hover:text-zinc-200"
                        :title="$t('app.nav_move_down')"
                        :aria-label="$t('app.nav_move_down')"
                        @click.stop="$emit('nav-reorder', { kind: 'group-offset', groupId: group.id, delta: 1 })"
                    >
                        <MaterialDesignIcon icon-name="chevron-down" class="size-4" />
                    </button>
                </template>
            </div>
            <ul
                class="py-1 space-y-1"
                :class="isCollapsed ? 'px-0' : 'pr-2'"
                @dragover.prevent="setNavDragOver(`group-end:${group.id}`, $event)"
                @drop.prevent="onGroupListDrop(group.id)"
            >
                <li
                    v-for="item in group.items"
                    :key="item.id"
                    class="flex items-center"
                    :class="[
                        isCollapsed ? 'justify-center' : '',
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
                    <SidebarLink
                        class="min-w-0 flex-1"
                        :to="item.route"
                        :is-collapsed="isCollapsed"
                        :edit-mode="isEditing"
                    >
                        <template #icon>
                            <span class="relative inline-flex shrink-0">
                                <MaterialDesignIcon
                                    :icon-name="item.icon"
                                    class="w-6 h-6 text-gray-700 dark:text-white"
                                />
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
        </template>

        <div
            v-if="moreNavItems.length > 0 || isEditing"
            class="mt-1 border-t border-gray-200 dark:border-zinc-800"
            :class="dragOverKey === 'more' ? 'bg-blue-50 dark:bg-blue-900/20' : ''"
        >
            <button
                type="button"
                class="flex w-full items-center gap-3 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:text-zinc-200 dark:hover:bg-zinc-800 transition-colors"
                :class="isCollapsed ? 'justify-center px-0' : 'px-4'"
                data-testid="sidebar-more-toggle"
                @pointerdown="onNavHoldPointerDown"
                @pointermove="onNavHoldPointerMove"
                @pointerup="onNavHoldPointerUp"
                @pointercancel="onNavHoldPointerUp"
                @click.capture="onNavHoldClickCapture"
                @contextmenu="onNavHoldContextMenu"
                @click="$emit('more-toggle')"
                @dragover.prevent="setNavDragOver('more', $event)"
                @drop.prevent="onMoreDrop"
            >
                <MaterialDesignIcon icon-name="dots-horizontal" class="size-6 shrink-0" />
                <span v-if="!isCollapsed" class="flex-1 text-left">{{ $t("app.nav_more") }}</span>
                <MaterialDesignIcon
                    v-if="!isCollapsed"
                    :icon-name="isShowingMoreNav ? 'chevron-up' : 'chevron-down'"
                    class="size-5 shrink-0 text-gray-400"
                />
            </button>
            <ul v-if="isShowingMoreNav && !isCollapsed" class="py-1 pr-2 space-y-1">
                <li
                    v-for="item in moreNavItems"
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
                        v-if="isEditing"
                        icon-name="drag-vertical"
                        class="ml-1 size-4 shrink-0 opacity-50"
                    />
                    <SidebarLink class="min-w-0 flex-1" :to="item.route" :is-collapsed="false" :edit-mode="isEditing">
                        <template #icon>
                            <MaterialDesignIcon :icon-name="item.icon" class="w-6 h-6 text-gray-700 dark:text-white" />
                        </template>
                        <template #text>
                            <span>{{ item.label || $t(item.labelKey) }}</span>
                        </template>
                    </SidebarLink>
                    <div v-if="isEditing" class="flex shrink-0 flex-col pr-1">
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
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SidebarLink from "../SidebarLink.vue";
import { navEditHoldMixin } from "../../js/appSidebarNavEditHold.js";

export default {
    name: "AppSidebarNav",
    components: {
        MaterialDesignIcon,
        SidebarLink,
    },
    mixins: [navEditHoldMixin],
    props: {
        primaryNavGroups: {
            type: Array,
            required: true,
        },
        moreNavItems: {
            type: Array,
            default: () => [],
        },
        isCollapsed: {
            type: Boolean,
            default: false,
        },
        isEditing: {
            type: Boolean,
            default: false,
        },
        isShowingMoreNav: {
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
    emits: ["more-toggle", "edit-start", "nav-reorder"],
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
        onGroupDragStart(groupId, event) {
            this.beginNavDrag("group", groupId, event);
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
            } else if (this.draggingKind === "group" && this.draggingId) {
                const group = this.primaryNavGroups.find((entry) => entry.items.some((item) => item.id === itemId));
                if (group && group.id !== this.draggingId) {
                    this.$emit("nav-reorder", {
                        kind: "group",
                        groupId: this.draggingId,
                        beforeGroupId: group.id,
                    });
                }
            }
            this.clearNavDrag();
        },
        onGroupHeaderDrop(groupId) {
            if (this.draggingKind === "item" && this.draggingId) {
                this.$emit("nav-reorder", {
                    kind: "item",
                    itemId: this.draggingId,
                    target: { type: "group-start", id: groupId },
                });
            } else if (this.draggingKind === "group" && this.draggingId && this.draggingId !== groupId) {
                this.$emit("nav-reorder", {
                    kind: "group",
                    groupId: this.draggingId,
                    beforeGroupId: groupId,
                });
            }
            this.clearNavDrag();
        },
        onGroupListDrop(groupId) {
            if (this.draggingKind === "item" && this.draggingId) {
                this.$emit("nav-reorder", {
                    kind: "item",
                    itemId: this.draggingId,
                    target: { type: "group-end", id: groupId },
                });
            }
            this.clearNavDrag();
        },
        onMoreDrop() {
            if (this.draggingKind === "item" && this.draggingId) {
                this.$emit("nav-reorder", {
                    kind: "item",
                    itemId: this.draggingId,
                    target: { type: "more-start" },
                });
            }
            this.clearNavDrag();
        },
    },
};
</script>
