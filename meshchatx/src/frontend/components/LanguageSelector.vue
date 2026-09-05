<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import LanguageSelectorSvelte from "../ui/svelte/LanguageSelector.svelte";

/**
 * Thin Vue host for the Svelte LanguageSelector
 */
export default {
    name: "LanguageSelector",
    props: {
        class: {
            type: String,
            default: "",
        },
    },
    emits: ["language-change"],
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
            this._svelte = mount(LanguageSelectorSvelte, {
                target: root,
                props: {
                    class: this.$attrs.class || this.class || "",
                    onlanguagechange: (code) => this.$emit("language-change", code),
                },
            });
        },
    },
};
</script>
