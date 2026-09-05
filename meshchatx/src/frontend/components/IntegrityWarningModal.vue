<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import IntegrityWarningModalSvelte from "../features/app-shell/components/IntegrityWarningModal.svelte";

/**
 * Thin Vue host for the Svelte IntegrityWarningModal
 */
export default {
    name: "IntegrityWarningModal",
    mounted() {
        this._svelte = mount(IntegrityWarningModalSvelte, {
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
        close() {
            return this._svelte?.close();
        },
        acknowledgeAndReset() {
            return this._svelte?.acknowledgeAndReset();
        },
    },
};
</script>
