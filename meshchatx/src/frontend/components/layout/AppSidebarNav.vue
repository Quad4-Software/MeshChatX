<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex-1 overflow-y-auto">
        <template v-for="group in primaryNavGroups" :key="group.id">
            <div
                v-if="!isCollapsed"
                class="px-4 pt-2 pb-1 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-zinc-500"
            >
                {{ $t(`app.nav_group.${group.id}`) }}
            </div>
            <ul class="py-1 pr-2 space-y-1">
                <li v-for="item in group.items" :key="item.id">
                    <SidebarLink :to="item.route" :is-collapsed="isCollapsed">
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
                </li>
            </ul>
        </template>

        <div v-if="moreNavItems.length > 0" class="mt-1 border-t border-gray-200 dark:border-zinc-800">
            <button
                type="button"
                class="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:text-zinc-200 dark:hover:bg-zinc-800 transition-colors"
                :class="isCollapsed ? 'justify-center' : ''"
                data-testid="sidebar-more-toggle"
                @click="$emit('more-toggle')"
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
                <li v-for="item in moreNavItems" :key="item.id">
                    <SidebarLink :to="item.route" :is-collapsed="false">
                        <template #icon>
                            <MaterialDesignIcon :icon-name="item.icon" class="w-6 h-6 text-gray-700 dark:text-white" />
                        </template>
                        <template #text>
                            <span>{{ item.label || $t(item.labelKey) }}</span>
                        </template>
                    </SidebarLink>
                </li>
            </ul>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SidebarLink from "../SidebarLink.vue";

export default {
    name: "AppSidebarNav",
    components: {
        MaterialDesignIcon,
        SidebarLink,
    },
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
    emits: ["more-toggle"],
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
    },
};
</script>
