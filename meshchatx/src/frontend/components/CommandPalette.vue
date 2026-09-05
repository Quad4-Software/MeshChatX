<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents"></div>
</template>

<script>
import { mount, unmount } from "svelte";
import CommandPaletteSvelte from "../features/app-shell/components/CommandPalette.svelte";

/**
 * Thin Vue host for the Svelte CommandPalette
 */
export default {
    name: "CommandPalette",
    created() {
        Object.defineProperty(this, "isOpen", {
            get: () => Boolean(this._svelte?.getIsOpen?.()),
            set: (val) => {
                if (val) {
                    this._svelte?.open?.();
                } else {
                    this._svelte?.close?.();
                }
            },
            configurable: true,
            enumerable: true,
        });
        Object.defineProperty(this, "query", {
            get: () => "",
            set: (val) => {
                this._svelte?.setQuery?.(val);
            },
            configurable: true,
            enumerable: true,
        });
        Object.defineProperty(this, "filteredResults", {
            get: () => this._svelte?.getFilteredResults?.() || [],
            configurable: true,
            enumerable: true,
        });
        Object.defineProperty(this, "groupedResults", {
            get: () => this._svelte?.getGroupedResults?.() || {},
            configurable: true,
            enumerable: true,
        });
        Object.defineProperty(this, "highlightedId", {
            get: () => this._svelte?.getHighlightedId?.() || null,
            set: (val) => {
                this._svelte?.setHighlightedId?.(val);
            },
            configurable: true,
            enumerable: true,
        });
        Object.defineProperty(this, "peers", {
            get: () => [],
            set: (val) => {
                this._svelte?.setPeers?.(val);
            },
            configurable: true,
            enumerable: true,
        });
        Object.defineProperty(this, "contacts", {
            get: () => [],
            set: (val) => {
                this._svelte?.setContacts?.(val);
            },
            configurable: true,
            enumerable: true,
        });
    },
    mounted() {
        this._svelte = mount(CommandPaletteSvelte, {
            target: this.$refs.root,
            props: {
                onnavigate: (route) => {
                    if (route && this.$router) {
                        this.$router.push(route);
                    }
                },
                onexecuteaction: () => {
                    this.executeAction();
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
        open() {
            return this._svelte?.open();
        },
        close() {
            return this._svelte?.close();
        },
        toggle() {
            return this._svelte?.toggle();
        },
        moveHighlight(step) {
            return this._svelte?.moveHighlight?.(step);
        },
        executeResult(result) {
            return this._svelte?.executeResult?.(result);
        },
        executeAction() {
            return this._svelte?.executeAction?.(true);
        },
    },
};
</script>
