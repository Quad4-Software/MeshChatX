// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * LXMF message forwarder rules UI.
 */
export function registerForwarderFeature(): void {
    registerFeature({
        id: "forwarder",
        routes: [
            {
                name: "forwarder",
                path: "/forwarder",
                mount: "svelte",
                load: () => import("./ForwarderPage.svelte"),
            },
        ],
    });
}
