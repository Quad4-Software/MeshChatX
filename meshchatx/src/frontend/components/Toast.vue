<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import ToastSvelte from "../ui/svelte/Toast.svelte";

/**
 * Thin Vue host for the Svelte Toast
 */
export default {
    name: "Toast",
    mounted() {
        this._svelte = mount(ToastSvelte, {
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
