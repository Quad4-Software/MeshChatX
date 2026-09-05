// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * LXMF sieve filters feature registration
 */
export function registerSieveFiltersFeature(): void {
    registerFeature({
        id: "sieve-filters",
        routes: [
            {
                name: "sieve-filters",
                path: "/tools/sieve-filters",
                mount: "svelte",
                load: () => import("./SieveFiltersPage.svelte"),
            },
        ],
    });
}
