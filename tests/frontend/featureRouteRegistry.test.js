// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { clearRoutes, listRoutes, registerRoute } from "../../meshchatx/src/frontend/js/registries/routeRegistry.js";
import {
    clearFeatureIds,
    listFeatureIds,
    registerFeature,
} from "../../meshchatx/src/frontend/js/registries/featureRegistry.js";
import { registerBlockedFeature } from "../../meshchatx/src/frontend/features/blocked/index.js";
import { buildRouterRoutesFromRegistry } from "../../meshchatx/src/frontend/shell/buildRouterRoutes.js";

describe("feature route registry", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("rejects routes without load or mount", () => {
        expect(() => registerRoute({ name: "x", path: "/x", mount: "vue" })).toThrow(/load/);
        expect(() =>
            registerRoute({
                name: "y",
                path: "/y",
                mount: "wat",
                load: () => Promise.resolve({}),
            })
        ).toThrow(/mount/);
    });

    it("registerFeature records routes and feature id", () => {
        registerFeature({
            id: "demo",
            routes: [
                {
                    name: "demo",
                    path: "/demo",
                    mount: "vue",
                    load: () => Promise.resolve({ default: {} }),
                },
            ],
        });
        expect(listFeatureIds()).toEqual(["demo"]);
        expect(listRoutes().map((r) => r.name)).toEqual(["demo"]);
    });

    it("blocked feature registers the blocked route", () => {
        registerBlockedFeature();
        const blocked = listRoutes().find((r) => r.name === "blocked");
        expect(blocked).toBeTruthy();
        expect(blocked.path).toBe("/blocked");
        expect(blocked.mount).toBe("svelte");
        expect(typeof blocked.load).toBe("function");
    });

    it("buildRouterRoutesFromRegistry maps svelte loads to FeaturePageHost", () => {
        registerBlockedFeature();
        const routes = buildRouterRoutesFromRegistry();
        const blocked = routes.find((r) => r.name === "blocked");
        expect(blocked).toBeTruthy();
        expect(blocked.component).toBeTruthy();
        expect(blocked.meta.featureMount).toBe("svelte");
        expect(typeof blocked.meta.featureLoad).toBe("function");
    });
});
