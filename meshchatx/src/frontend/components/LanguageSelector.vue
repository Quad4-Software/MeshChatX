<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import LanguageSelectorSvelte from "../ui/svelte/LanguageSelector.svelte";
import { createThinSvelteHost } from "../js/svelteVueHost";

const svelteHost = createThinSvelteHost({
    component: LanguageSelectorSvelte,
    buildProps(vm) {
        return {
            class: vm.$attrs.class || vm.class || "",
            onlanguagechange: (code) => vm.$emit("language-change", code),
        };
    },
    extraWatch: {
        "$attrs.class"() {
            this._syncSvelteProps();
        },
    },
});

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
    ...svelteHost,
};
</script>
