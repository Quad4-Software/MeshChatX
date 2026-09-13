// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Reticulum network status feature registration.
 */
export function registerRNStatusFeature(): void {
    registerFeature({
        id: "rnstatus",
        routes: [
            {
                name: "rnstatus",
                path: "/rnstatus",
                mount: "svelte",
                load: () => import("./RNStatusPage.svelte"),
            },
        ],
    });
}
