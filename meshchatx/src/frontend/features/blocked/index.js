// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Quiet leaf feature used to prove registerFeature + Svelte mount.
 */
export function registerBlockedFeature() {
    registerFeature({
        id: "blocked",
        routes: [
            {
                name: "blocked",
                path: "/blocked",
                mount: "svelte",
                load: () => import("./BlockedPage.svelte"),
            },
        ],
    });
}
