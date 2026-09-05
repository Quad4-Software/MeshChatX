<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import AppIdentitySwitchOverlaySvelte from "../../features/app-shell/components/AppIdentitySwitchOverlay.svelte";
import { createThinSvelteHost } from "../../js/svelteVueHost";

const svelteHost = createThinSvelteHost({
    component: AppIdentitySwitchOverlaySvelte,
    buildProps(vm) {
        return {
            show: vm.show,
            logoUrl: vm.logoUrl,
        };
    },
});

/**
 * Thin Vue host for the Svelte AppIdentitySwitchOverlay.
 */
export default {
    name: "AppIdentitySwitchOverlay",
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        logoUrl: {
            type: String,
            required: true,
        },
    },
    ...svelteHost,
};
</script>
