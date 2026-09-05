<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import ChannelPromptModalSvelte from "../features/app-shell/components/ChannelPromptModal.svelte";

/**
 * Thin Vue host for the Svelte ChannelPromptModal
 */
export default {
    name: "ChannelPromptModal",
    data() {
        return {
            visible: false,
        };
    },
    mounted() {
        this._svelte = mount(ChannelPromptModalSvelte, {
            target: this.$refs.root,
        });
    },
    beforeUnmount() {
        if (this._svelte) {
            unmount(this._svelte);
            this._svelte = null;
        }
    },
    methods: {
        show(appInfo) {
            const shown = this._svelte?.show(appInfo);
            this.visible = Boolean(shown);
            return Boolean(shown);
        },
        async onDismiss() {
            await this._svelte?.onDismiss();
            this.visible = false;
        },
        async onSecondary() {
            await this._svelte?.onSecondary();
        },
    },
};
</script>
