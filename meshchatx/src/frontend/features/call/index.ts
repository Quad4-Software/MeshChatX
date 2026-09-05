// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Call / LXST telephone feature registration
 */
export function registerCallFeature(): void {
    registerFeature({
        id: "call",
        routes: [
            {
                name: "call",
                path: "/call",
                mount: "svelte",
                load: () => import("./CallPage.svelte"),
            },
            {
                name: "call-popout",
                path: "/popout/call",
                mount: "svelte",
                meta: { isPopout: true },
                load: () => import("./CallPage.svelte"),
            },
        ],
    });
}
