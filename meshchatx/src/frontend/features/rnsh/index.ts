// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Reticulum remote shell feature registration
 */
export function registerRnshFeature(): void {
    registerFeature({
        id: "rnsh",
        routes: [
            {
                name: "rnsh",
                path: "/rnsh",
                mount: "svelte",
                load: () => import("./RNSHPage.svelte"),
            },
        ],
    });
}

export const registerRNSHFeature = registerRnshFeature;
