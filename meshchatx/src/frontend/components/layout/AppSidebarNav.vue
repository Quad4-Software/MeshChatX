<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import AppSidebarNavSvelte from "../../features/app-shell/components/AppSidebarNav.svelte";
import { createThinSvelteHost } from "../../js/svelteVueHost";

const svelteHost = createThinSvelteHost({
    component: AppSidebarNavSvelte,
    buildProps(vm) {
        return {
            primaryNavGroups: vm.primaryNavGroups,
            moreNavItems: vm.moreNavItems,
            isCollapsed: vm.isCollapsed,
            isEditing: vm.isEditing,
            isShowingMoreNav: vm.isShowingMoreNav,
            unreadConversationsCount: vm.unreadConversationsCount,
            relayChatUnreadCount: vm.relayChatUnreadCount,
            missedCallsCount: vm.missedCallsCount,
            activeRouteName: vm.$route?.name || "",
            onmoretoggle: () => vm.$emit("more-toggle"),
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
 * Thin Vue host for the Svelte AppSidebarNav
 */
export default {
    name: "AppSidebarNav",
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
    ...svelteHost,
};
</script>
