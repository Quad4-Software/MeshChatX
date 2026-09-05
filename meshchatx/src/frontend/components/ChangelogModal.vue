<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import ChangelogModalSvelte from "../features/app-shell/components/ChangelogModal.svelte";
import { createThinSvelteHost } from "../js/svelteVueHost";

const svelteHost = createThinSvelteHost({
    component: ChangelogModalSvelte,
    buildProps(vm) {
        return {
            appVersion: vm.appVersion,
            isPage: Boolean(vm.$route?.meta?.isPage),
        };
    },
    extraWatch: {
        "$route.name"() {
            this._syncSvelteProps();
        },
    },
});

/**
 * Thin Vue host for the Svelte ChangelogModal
 */
export default {
    name: "ChangelogModal",
    props: {
        appVersion: {
            type: String,
            default: "",
        },
    },
    ...svelteHost,
    methods: {
        ...svelteHost.methods,
        show() {
            return this._svelte?.show();
        },
        close() {
            return this._svelte?.close();
        },
        fetchChangelog() {
            return this._svelte?.fetchChangelog();
        },
        markAsSeen() {
            return this._svelte?.markAsSeen();
        },
    },
};
</script>
