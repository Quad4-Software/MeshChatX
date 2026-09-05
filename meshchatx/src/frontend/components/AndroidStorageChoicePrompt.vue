<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import AndroidStorageChoicePromptSvelte from "../features/app-shell/components/AndroidStorageChoicePrompt.svelte";
import { createThinSvelteHost } from "../js/svelteVueHost";

const svelteHost = createThinSvelteHost({
    component: AndroidStorageChoicePromptSvelte,
    buildProps(vm) {
        return {
            variant: vm.variant,
            oncompleted: (payload) => vm.$emit("completed", payload),
            ondismissed: () => {
                vm.visible = false;
                vm.$emit("dismissed");
            },
        };
    },
});

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
    ...svelteHost,
    methods: {
        ...svelteHost.methods,
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
