// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Reticulum network path trace feature registration
 */
export function registerRnpathTraceFeature(): void {
    registerFeature({
        id: "rnpath-trace",
        routes: [
            {
                name: "rnpath-trace",
                path: "/rnpath-trace",
                mount: "svelte",
                load: () => import("./RNPathTracePage.svelte"),
            },
        ],
    });
}
