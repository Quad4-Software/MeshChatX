<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import AppSidebarClassicNavSvelte from "../../features/app-shell/components/AppSidebarClassicNav.svelte";
import { createThinSvelteHost } from "../../js/svelteVueHost";

const svelteHost = createThinSvelteHost({
    component: AppSidebarClassicNavSvelte,
    buildProps(vm) {
        return {
            navItems: vm.navItems,
            isCollapsed: vm.isCollapsed,
            isEditing: vm.isEditing,
            unreadConversationsCount: vm.unreadConversationsCount,
            relayChatUnreadCount: vm.relayChatUnreadCount,
            missedCallsCount: vm.missedCallsCount,
            activeRouteName: vm.$route?.name || "",
            oneditstart: () => vm.$emit("edit-start"),
            onnavreorder: (payload) => vm.$emit("nav-reorder", payload),
        };
    },
    extraWatch: {
        "$route.name"() {
            this._syncSvelteProps();
        },
    },
});

/**
 * Thin Vue host for the Svelte AppSidebarClassicNav
 */
export default {
    name: "AppSidebarClassicNav",
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
    ...svelteHost,
};
</script>
