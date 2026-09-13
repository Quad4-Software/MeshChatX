// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Reticulum remote execution feature registration
 */
export function registerRnxFeature(): void {
    registerFeature({
        id: "rnx",
        routes: [
            {
                name: "rnx",
                path: "/rnx",
                mount: "svelte",
                load: () => import("./RNXPage.svelte"),
            },
        ],
    });
}
