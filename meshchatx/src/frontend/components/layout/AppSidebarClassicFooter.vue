<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import AppSidebarClassicFooterSvelte from "../../features/app-shell/components/AppSidebarClassicFooter.svelte";
import { createThinSvelteHost } from "../../js/svelteVueHost";

const svelteHost = createThinSvelteHost({
    component: AppSidebarClassicFooterSvelte,
    buildProps(vm) {
        return {
            config: vm.config,
            displayName: vm.displayName,
            identityLabel: vm.identityLabel,
            lastAnnouncedLabel: vm.lastAnnouncedLabel,
            isCollapsed: vm.isCollapsed,
            onupdatedisplayname: (val) => vm.$emit("update:displayName", val),
            onsaveidentity: () => vm.$emit("save-identity"),
            onsendannounce: () => vm.$emit("send-announce"),
            onannounceintervalchange: (val) => vm.$emit("announce-interval-change", val),
            oncopyvalue: (val, label) => vm.$emit("copy-value", val, label),
            onopenlxmfqr: () => vm.$emit("open-lxmf-qr"),
        };
    },
});

/**
 * Thin Vue host for the Svelte AppSidebarClassicFooter
 */
export default {
    name: "AppSidebarClassicFooter",
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
    ...svelteHost,
};
</script>
