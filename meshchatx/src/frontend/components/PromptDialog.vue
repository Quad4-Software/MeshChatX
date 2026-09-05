<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import PromptDialogSvelte from "../ui/svelte/PromptDialog.svelte";

/**
 * Thin Vue host for the Svelte PromptDialog
 */
export default {
    name: "PromptDialog",
    mounted() {
        this._svelte = mount(PromptDialogSvelte, {
            target: this.$refs.root,
        });
    },
    beforeUnmount() {
        if (this._svelte) {
            unmount(this._svelte);
            this._svelte = null;
        }
    },
};
</script>
