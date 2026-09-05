<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import ConfirmDialogSvelte from "../ui/svelte/ConfirmDialog.svelte";

/**
 * Thin Vue host for the Svelte ConfirmDialog. App.vue keeps importing this file.
 */
export default {
    name: "ConfirmDialog",
    mounted() {
        this._svelte = mount(ConfirmDialogSvelte, {
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
