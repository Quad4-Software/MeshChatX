// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Discovered and local propagation node manager for LXMF messaging.
 */
export function registerPropagationNodesFeature(): void {
    registerFeature({
        id: "propagation-nodes",
        routes: [
            {
                name: "propagation-nodes",
                path: "/propagation-nodes",
                mount: "svelte",
                load: () => import("./PropagationNodesPage.svelte"),
            },
        ],
    });
}
