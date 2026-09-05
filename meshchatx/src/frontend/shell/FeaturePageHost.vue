<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="root" class="feature-page-host flex flex-1 min-h-0 h-full min-w-0 w-full overflow-hidden"></div>
</template>

<script>
import { defineComponent } from "vue";
import { mount, unmount } from "svelte";

/**
 * Vue route host that mounts a Svelte page from route.meta.featureLoad
 */
export default defineComponent({
    name: "FeaturePageHost",
    data() {
        return {
            /** @type {Record<string, unknown> | null} */
            svelteApp: null,
            svelteRemounting: false,
        };
    },
    computed: {
        featureRouteKey() {
            const route = this.$route;
            if (!route) {
                return "";
            }
            const meta = route.meta || {};
            const load = meta.featureLoad;
            const loadKey = typeof load === "function" ? load.name || "featureLoad" : "";
            return `${String(route.name || "")}:${JSON.stringify(route.params || {})}:${loadKey}`;
        },
    },
    watch: {
        featureRouteKey(newKey, oldKey) {
            if (newKey !== oldKey) {
                this.remount();
            }
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
            if (this.svelteRemounting) {
                return;
            }
            this.svelteRemounting = true;
            const routeKey = this.featureRouteKey;
            try {
                this.teardown();
                const meta = this.$route && this.$route.meta ? this.$route.meta : {};
                const load = meta.featureLoad;
                if (typeof load !== "function") {
                    console.error("FeaturePageHost: missing featureLoad on route", this.$route && this.$route.name);
                    return;
                }
                const mod = await load();
                if (routeKey !== this.featureRouteKey) {
                    return;
                }
                const Comp = (mod && typeof mod === "object" && "default" in mod ? mod.default : mod) || mod;
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
            } finally {
                this.svelteRemounting = false;
            }
        },
    },
});
</script>
