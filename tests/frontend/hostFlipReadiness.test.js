// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { existsSync } from "fs";
import { join } from "path";
import { listNavItems } from "../../meshchatx/src/frontend/js/registries/navRegistry.js";
import { listRoutes } from "../../meshchatx/src/frontend/js/registries/routeRegistry.js";

const repoRoot = process.cwd();

/**
 * Host flip complete: live boot is App.svelte + hashRouter + PageOutlet.
 * Registry routes must stay mount svelte.
 */
describe("host flip readiness", () => {
    it("svelte shell and hash router exist", () => {
        expect(existsSync(join(repoRoot, "meshchatx/src/frontend/features/app-shell/App.svelte"))).toBe(true);
        expect(existsSync(join(repoRoot, "meshchatx/src/frontend/shell/hashRouter.ts"))).toBe(true);
        expect(existsSync(join(repoRoot, "meshchatx/src/frontend/shell/PageOutlet.svelte"))).toBe(true);
        expect(existsSync(join(repoRoot, "meshchatx/src/frontend/features/registerAllFeatures.ts"))).toBe(true);
    });

    it("nav and route registries expose list APIs", () => {
        expect(typeof listNavItems).toBe("function");
        expect(typeof listRoutes).toBe("function");
        expect(Array.isArray(listNavItems())).toBe(true);
        expect(Array.isArray(listRoutes())).toBe(true);
    });

    it("all registered routes mount as svelte", async () => {
        const { registerAllFeatures } = await import("../../meshchatx/src/frontend/features/registerAllFeatures.js");
        registerAllFeatures();
        const routes = listRoutes();
        expect(routes.length).toBeGreaterThan(0);
        const nonSvelte = routes.filter((r) => r.mount !== "svelte");
        expect(nonSvelte).toEqual([]);
    }, 30000);
});
