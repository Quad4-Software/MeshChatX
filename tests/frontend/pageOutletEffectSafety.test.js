// SPDX-License-Identifier: 0BSD

/**
 * PageOutlet must not track $state page-prop syncs inside its route $effect.
 * Otherwise stableKey conversation switches hit effect_update_depth_exceeded
 * and leave the outlet stuck on messages while the hash keeps changing.
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("PageOutlet effect safety", () => {
    it("untracks render so syncProps cannot re-enter the route effect", () => {
        const outlet = src("meshchatx/src/frontend/shell/PageOutlet.svelte");
        expect(outlet).toContain('import { mount, onDestroy, unmount, untrack } from "svelte"');
        expect(outlet).toContain("untrack(() => {");
        expect(outlet).toContain("void render(route)");
        expect(outlet).toMatch(/\$effect\(\(\) => \{[\s\S]*untrack\(\(\) => \{[\s\S]*void render\(route\)/);
        expect(outlet).toContain("effect_update_depth_exceeded");
    });

    it("keeps stableKey remount identity on route name only", () => {
        const keyMod = src("meshchatx/src/frontend/shell/pageOutletMountKey.ts");
        expect(keyMod).toContain("route.meta?.stableKey || route.meta?.keepAlive");
        expect(keyMod).toContain("return String(route.name)");
        expect(keyMod).not.toContain("JSON.stringify(route.params)");
    });
});
