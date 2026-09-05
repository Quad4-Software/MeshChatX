// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { existsSync } from "fs";
import { join } from "path";
import { listNavItems } from "../../meshchatx/src/frontend/js/registries/navRegistry.js";
import { listRoutes } from "../../meshchatx/src/frontend/js/registries/routeRegistry.js";

const repoRoot = process.cwd();

/**
 * Host flip readiness: shell may move from Vue App.vue to Svelte when these
 * surfaces stay registry-driven. Do not flip while Vue pages still dominate.
 */
describe("host flip readiness", () => {
    it("shell helpers for registry routes exist", () => {
        expect(existsSync(join(repoRoot, "meshchatx/src/frontend/shell/FeaturePageHost.vue"))).toBe(true);
        expect(existsSync(join(repoRoot, "meshchatx/src/frontend/shell/buildRouterRoutes.ts"))).toBe(true);
        expect(existsSync(join(repoRoot, "meshchatx/src/frontend/features/registerAllFeatures.ts"))).toBe(true);
    });

    it("nav and route registries expose list APIs for a future Svelte shell", () => {
        expect(typeof listNavItems).toBe("function");
        expect(typeof listRoutes).toBe("function");
        expect(Array.isArray(listNavItems())).toBe(true);
        expect(Array.isArray(listRoutes())).toBe(true);
    });

    it("documents that Vue remains host until mount vue count is zero", () => {
        // Intentional gate: a Svelte app shell replaces App.vue only after every
        // route uses mount svelte (or is deleted). This test stays green while
        // dual-stack runs.
        const vueMounts = listRoutes().filter((r) => r.mount === "vue");
        expect(vueMounts.every((r) => typeof r.load === "function")).toBe(true);
    });
});
