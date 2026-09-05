<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import PostInstallPromptHostSvelte from "../features/app-shell/components/PostInstallPromptHost.svelte";

/**
 * Thin Vue host for the Svelte PostInstallPromptHost
 */
export default {
    name: "PostInstallPromptHost",
    emits: ["completed", "dismissed"],
    data() {
        return {
            visible: false,
            activeEntry: null,
        };
    },
    mounted() {
        this._svelte = mount(PostInstallPromptHostSvelte, {
            target: this.$refs.root,
            props: {
                oncompleted: (payload) => {
                    this.visible = false;
                    this.activeEntry = null;
                    this.$emit("completed", payload);
                },
                ondismissed: () => {
                    this.visible = false;
                    this.activeEntry = null;
                    this.$emit("dismissed");
                },
            },
        });
    },
    beforeUnmount() {
        if (this._svelte) {
            unmount(this._svelte);
            this._svelte = null;
        }
    },
    methods: {
        async showNext() {
            const shown = await this._svelte?.showNext();
            this.visible = Boolean(shown);
            this.activeEntry = await this.findNextPending();
            return Boolean(shown);
        },
        findNextPending() {
            return this._svelte?.findNextPending();
        },
        hide() {
            this._svelte?.hide();
            this.visible = false;
            this.activeEntry = null;
        },
        dismissActive() {
            this._svelte?.dismissActive();
            this.visible = false;
            this.activeEntry = null;
        },
        async onPrimary() {
            await this._svelte?.onPrimary();
        },
        async onSecondary() {
            await this._svelte?.onSecondary();
        },
        onVisibleUpdate(val) {
            if (!val) {
                this.hide();
                this.$emit("dismissed");
            }
        },
    },
};
</script>
