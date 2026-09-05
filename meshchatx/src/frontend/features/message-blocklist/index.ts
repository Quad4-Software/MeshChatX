// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Register the LXMF message blocklist tool feature
 */
export function registerMessageBlocklistFeature(): void {
    registerFeature({
        id: "message-blocklist",
        routes: [
            {
                name: "message-blocklist",
                path: "/tools/message-blocklist",
                mount: "svelte",
                load: () => import("./MessageBlocklistPage.svelte"),
            },
        ],
    });
}
