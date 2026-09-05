<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import AppSidebarClassicNavSvelte from "../../features/app-shell/components/AppSidebarClassicNav.svelte";

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
            this._svelte = mount(AppSidebarClassicNavSvelte, {
                target: root,
                props: {
                    navItems: this.navItems,
                    isCollapsed: this.isCollapsed,
                    isEditing: this.isEditing,
                    unreadConversationsCount: this.unreadConversationsCount,
                    relayChatUnreadCount: this.relayChatUnreadCount,
                    missedCallsCount: this.missedCallsCount,
                    activeRouteName: this.$route?.name || "",
                    oneditstart: () => this.$emit("edit-start"),
                    onnavreorder: (payload) => this.$emit("nav-reorder", payload),
                },
            });
        },
    },
};
</script>
