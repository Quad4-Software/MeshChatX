<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import AppSidebarAccountFooterSvelte from "../../features/app-shell/components/AppSidebarAccountFooter.svelte";

/**
 * Thin Vue host for the Svelte AppSidebarAccountFooter
 */
export default {
    name: "AppSidebarAccountFooter",
    props: {
        config: {
            type: Object,
            required: true,
        },
        displayName: {
            type: String,
            default: "",
        },
        identityLabel: {
            type: String,
            required: true,
        },
        lastAnnouncedLabel: {
            type: String,
            default: "",
        },
        isCollapsed: {
            type: Boolean,
            default: false,
        },
    },
    emits: [
        "update:displayName",
        "save-identity",
        "send-announce",
        "announce-interval-change",
        "copy-value",
        "open-lxmf-qr",
    ],
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
            this._svelte = mount(AppSidebarAccountFooterSvelte, {
                target: root,
                props: {
                    config: this.config,
                    displayName: this.displayName,
                    identityLabel: this.identityLabel,
                    lastAnnouncedLabel: this.lastAnnouncedLabel,
                    isCollapsed: this.isCollapsed,
                    onupdatedisplayname: (val) => this.$emit("update:displayName", val),
                    onsaveidentity: () => this.$emit("save-identity"),
                    onsendannounce: () => this.$emit("send-announce"),
                    onannounceintervalchange: (val) => this.$emit("announce-interval-change", val),
                    oncopyvalue: (val, label) => this.$emit("copy-value", val, label),
                    onopenlxmfqr: () => this.$emit("open-lxmf-qr"),
                    onnavigatetoidentities: () => {
                        if (this.$router) {
                            this.$router.push({ name: "identities" });
                        }
                    },
                },
            });
        },
    },
};
</script>
