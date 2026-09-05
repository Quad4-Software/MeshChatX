<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import AppSidebarNavSvelte from "../../features/app-shell/components/AppSidebarNav.svelte";

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
    mounted() {
        this.remount();
    },
    updated() {
        this.remount();
    },
    beforeUnmount() {
        this.teardown();
    },
    methods: {
        teardown() {
            if (this._svelte) {
                unmount(this._svelte);
                this._svelte = null;
            }
        },
        remount() {
            this.teardown();
            const root = this.$refs.root;
            if (!root) return;
            this._svelte = mount(AppSidebarNavSvelte, {
                target: root,
                props: {
                    primaryNavGroups: this.primaryNavGroups,
                    moreNavItems: this.moreNavItems,
                    isCollapsed: this.isCollapsed,
                    isEditing: this.isEditing,
                    isShowingMoreNav: this.isShowingMoreNav,
                    unreadConversationsCount: this.unreadConversationsCount,
                    relayChatUnreadCount: this.relayChatUnreadCount,
                    missedCallsCount: this.missedCallsCount,
                    activeRouteName: this.$route?.name || "",
                    onmoretoggle: () => this.$emit("more-toggle"),
                    oneditstart: () => this.$emit("edit-start"),
                    onnavreorder: (payload) => this.$emit("nav-reorder", payload),
                },
            });
        },
    },
};
</script>
