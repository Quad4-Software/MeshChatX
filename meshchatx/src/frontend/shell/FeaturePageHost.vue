<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="contents feature-page-host"></div>
</template>

<script>
import { mount, unmount } from "svelte";

/**
 * Vue route host that mounts a Svelte page from route.meta.featureLoad.
 */
export default {
    name: "FeaturePageHost",
    data() {
        return {
            svelteApp: null,
        };
    },
    watch: {
        $route() {
            this.remount();
        },
    },
    mounted() {
        this.remount();
    },
    beforeUnmount() {
        this.teardown();
    },
    methods: {
        teardown() {
            if (this.svelteApp) {
                try {
                    unmount(this.svelteApp);
                } catch {
                    /* already gone */
                }
                this.svelteApp = null;
            }
            const root = this.$refs.root;
            if (root) {
                root.replaceChildren();
            }
        },
        async remount() {
            this.teardown();
            const meta = this.$route && this.$route.meta ? this.$route.meta : {};
            const load = meta.featureLoad;
            if (typeof load !== "function") {
                console.error("FeaturePageHost: missing featureLoad on route", this.$route && this.$route.name);
                return;
            }
            const mod = await load();
            const Comp = mod && (mod.default || mod);
            if (!Comp) {
                console.error("FeaturePageHost: load() returned no default export");
                return;
            }
            const root = this.$refs.root;
            if (!root) {
                return;
            }
            this.svelteApp = mount(Comp, {
                target: root,
                props: {
                    ...(this.$route.params || {}),
                    routeQuery: { ...(this.$route.query || {}) },
                },
            });
        },
    },
};
</script>
