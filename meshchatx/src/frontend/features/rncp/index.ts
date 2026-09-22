// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerRncpFeature(): void {
    registerFeature({
        id: "rncp",
        routes: [
            {
                name: "rncp",
                path: "/rncp",
                mount: "svelte",
                load: () => import("./RNCPPage.svelte"),
            },
        ],
    });
}
