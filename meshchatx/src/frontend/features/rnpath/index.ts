// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerRNPathFeature(): void {
    registerFeature({
        id: "rnpath",
        routes: [
            {
                name: "rnpath",
                path: "/rnpath",
                mount: "svelte",
                load: () => import("./RNPathPage.svelte"),
            },
        ],
    });
}

export const registerRnpathFeature = registerRNPathFeature;
