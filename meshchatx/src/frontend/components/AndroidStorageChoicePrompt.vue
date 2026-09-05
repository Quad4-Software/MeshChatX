<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import AndroidStorageChoicePromptSvelte from "../features/app-shell/components/AndroidStorageChoicePrompt.svelte";

/**
 * Thin Vue host for the Svelte AndroidStorageChoicePrompt
 */
export default {
    name: "AndroidStorageChoicePrompt",
    props: {
        variant: {
            type: String,
            default: "upgrade",
            validator: (v) => v === "setup" || v === "upgrade",
        },
    },
    emits: ["completed", "dismissed"],
    data() {
        return {
            visible: false,
        };
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
            this._svelte = mount(AndroidStorageChoicePromptSvelte, {
                target: root,
                props: {
                    variant: this.variant,
                    oncompleted: (payload) => this.$emit("completed", payload),
                    ondismissed: () => {
                        this.visible = false;
                        this.$emit("dismissed");
                    },
                },
            });
        },
        refreshStatus() {
            return this._svelte?.refreshStatus();
        },
        shouldShowSetup() {
            return this._svelte?.shouldShowSetup();
        },
        shouldShowUpgrade() {
            return this._svelte?.shouldShowUpgrade();
        },
        showSetup() {
            const shown = this._svelte?.showSetup();
            this.visible = Boolean(shown);
            return Boolean(shown);
        },
        showUpgrade() {
            const shown = this._svelte?.showUpgrade();
            this.visible = Boolean(shown);
            return Boolean(shown);
        },
        hide() {
            this._svelte?.hide();
            this.visible = false;
        },
        async onPrimary() {
            await this._svelte?.onPrimary();
        },
        async onSecondary() {
            await this._svelte?.onSecondary();
        },
    },
};
</script>
