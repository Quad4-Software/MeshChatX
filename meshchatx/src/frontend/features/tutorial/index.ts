// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Tutorial feature: /tutorial route.
 * The page is a native Svelte 5 wizard. The same steps render inside the shell
 * modal through TutorialModalHost.
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
