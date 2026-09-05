// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerNetworkVisualiserFeature(): void {
    registerFeature({
        id: "network-visualiser",
        routes: [
            {
                name: "network-visualiser",
                path: "/network-visualiser",
                mount: "svelte",
                load: () => import("./NetworkVisualiserPage.svelte"),
            },
        ],
    });
}
