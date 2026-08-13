<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex-1 overflow-y-auto">
        <ul class="py-3 pr-2 space-y-1">
            <li v-for="item in navItems" :key="item.id">
                <SidebarLink :to="item.route" :is-collapsed="isCollapsed">
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
            </li>
        </ul>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SidebarLink from "../SidebarLink.vue";

export default {
    name: "AppSidebarClassicNav",
    components: {
        MaterialDesignIcon,
        SidebarLink,
    },
    props: {
        navItems: {
            type: Array,
            required: true,
        },
        isCollapsed: {
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
