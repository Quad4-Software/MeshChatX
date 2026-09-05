// SPDX-License-Identifier: 0BSD

/**
 * Mount a single Vue SFC as an island inside the Svelte shell.
 * Interim bridge for components that are not ported yet (Tutorial). The island
 * gets vue-i18n plus router shaped globals backed by hashRouter, so Options API
 * code keeps working without vue-router.
 * Remove once no Vue SFC is mounted at runtime.
 */

import { createApp } from "vue";
import type { App, Component, Directive, Plugin } from "vue";
import { getCurrentRoute, router } from "./hashRouter.js";

interface IslandPlugins {
    i18n?: Plugin | null;
    directives?: Record<string, Directive>;
}

let islandPlugins: IslandPlugins = {};

/**
 * Register the plugins every Vue island should receive. Call once at boot.
 */
export function configureVueIslands(plugins: IslandPlugins): void {
    islandPlugins = plugins || {};
}

export interface VueIsland {
    app: App;
    vm: Record<string, any>;
    unmount: () => void;
}

/**
 * Create and mount a Vue island into target.
 */
export function mountVueIsland(
    component: Component,
    target: Element,
    props: Record<string, unknown> = {}
): VueIsland {
    const app = createApp(component, { ...props });
    if (islandPlugins.i18n) {
        app.use(islandPlugins.i18n);
    }
    for (const [name, directive] of Object.entries(islandPlugins.directives || {})) {
        app.directive(name, directive);
    }
    // Options API code reaches for $router / $route. hashRouter covers the
    // members MeshChatX uses, so the vue-router shape is deliberately partial.
    const globals = app.config.globalProperties as unknown as Record<string, unknown>;
    globals.$router = router;
    Object.defineProperty(globals, "$route", {
        configurable: true,
        get: () => getCurrentRoute() ?? { name: "", params: {}, query: {}, meta: {}, hash: "" },
    });
    const vm = app.mount(target) as unknown as Record<string, any>;
    return {
        app,
        vm,
        unmount: () => {
            try {
                app.unmount();
            } catch {
                /* already gone */
            }
        },
    };
}
