// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Reticulum mesh server / page nodes feature registration
 */
export function registerPageNodesFeature(): void {
    registerFeature({
        id: "page-nodes",
        routes: [
            {
                name: "mesh-server",
                path: "/mesh-server",
                mount: "svelte",
                load: () => import("./PageNodesPage.svelte"),
            },
        ],
    });
}
