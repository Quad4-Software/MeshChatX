<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import BlockedPageSvelte from "../../features/blocked/BlockedPage.svelte";

/**
 * Legacy Vue path for tests and any remaining direct imports.
 * Production routing uses FeaturePageHost + registerFeature (mount: svelte).
 */
export default {
    name: "BlockedPage",
    mounted() {
        this._svelte = mount(BlockedPageSvelte, {
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
