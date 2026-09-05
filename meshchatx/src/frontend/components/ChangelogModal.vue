<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import ChangelogModalSvelte from "../features/app-shell/components/ChangelogModal.svelte";

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
            this._svelte = mount(ChangelogModalSvelte, {
                target: root,
                props: {
                    appVersion: this.appVersion,
                    isPage: Boolean(this.$route?.meta?.isPage),
                },
            });
        },
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
