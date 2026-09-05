// SPDX-License-Identifier: 0BSD

import { listRoutes } from "../js/registries/routeRegistry.js";
import FeaturePageHost from "./FeaturePageHost.vue";

/**
 * Build vue-router route records from the route registry.
 * Vue mounts resolve the SFC directly. Svelte mounts use FeaturePageHost.
 * Lives in shell/ so kernel js/ stays free of Vue imports.
 * @returns {import('vue-router').RouteRecordRaw[]}
 */
export function buildRouterRoutesFromRegistry() {
    return listRoutes().map((entry) => {
        /** @type {import('vue-router').RouteRecordRaw} */
        const record = {
            name: entry.name,
            path: entry.path,
            meta: {
                ...(entry.meta || {}),
                featureMount: entry.mount,
            },
        };
        if (entry.props === true) {
            record.props = true;
        } else if (entry.routeProps && typeof entry.routeProps === "object") {
            record.props = entry.routeProps;
        }

        if (entry.mount === "svelte") {
            record.component = FeaturePageHost;
            record.meta.featureLoad = entry.load;
            return record;
        }

        record.component = () =>
            entry.load().then((mod) => {
                const Comp = mod && (mod.default || mod);
                if (!Comp) {
                    throw new Error(`routeRegistry: vue load for "${entry.name}" has no default export`);
                }
                return Comp;
            });
        return record;
    });
}
