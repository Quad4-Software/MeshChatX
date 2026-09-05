// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Tutorial feature: /tutorial route.
 * The page still wraps TutorialModal.vue through a Vue island. Swap the load
 * target for a native Svelte page once the tutorial is ported.
 */
export function registerTutorialFeature(): void {
    registerFeature({
        id: "tutorial",
        routes: [
            {
                name: "tutorial",
                path: "/tutorial",
                mount: "svelte",
                load: () => import("./TutorialPage.svelte"),
                meta: { isPage: true },
            },
        ],
    });
}
