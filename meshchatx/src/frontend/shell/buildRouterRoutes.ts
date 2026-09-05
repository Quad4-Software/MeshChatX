// SPDX-License-Identifier: 0BSD

// @ts-nocheck
import { listRoutes } from "../js/registries/routeRegistry.js";
import FeaturePageHost from "./FeaturePageHost.vue";
import type { Component } from "vue";
import type { RouteRecordRaw } from "vue-router";

export function buildRouterRoutesFromRegistry(): RouteRecordRaw[] {
    return listRoutes().map((entry) => {
        const record = {
            name: entry.name,
            path: entry.path,
            meta: {
                ...(entry.meta || {}),
                featureMount: entry.mount,
            },
        } as RouteRecordRaw;
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
                const moduleValue = mod as { default?: Component } | Component | null;
                    const Comp =
                        moduleValue && typeof moduleValue === "object" && "default" in moduleValue
                            ? moduleValue.default
                            : moduleValue;
                if (!Comp) {
                    throw new Error(`routeRegistry: vue load for "${entry.name}" has no default export`);
                }
                return Comp;
            });
        return record;
    });
}
