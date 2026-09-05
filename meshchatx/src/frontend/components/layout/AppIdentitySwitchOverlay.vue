<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import AppIdentitySwitchOverlaySvelte from "../../features/app-shell/components/AppIdentitySwitchOverlay.svelte";

/**
 * Thin Vue host for the Svelte AppIdentitySwitchOverlay.
 */
export default {
    name: "AppIdentitySwitchOverlay",
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        logoUrl: {
            type: String,
            required: true,
        },
    },
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
            this._svelte = mount(AppIdentitySwitchOverlaySvelte, {
                target: root,
                props: {
                    show: this.show,
                    logoUrl: this.logoUrl,
                },
            });
        },
    },
};
</script>
