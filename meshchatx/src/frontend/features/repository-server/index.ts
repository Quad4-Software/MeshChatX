// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";
import { FEATURE_ID, ROUTE_NAME, ROUTE_PATH } from "./lib/constants.js";

/**
 * Register the repository server tool feature
 */
export function registerRepositoryServerFeature(): void {
    registerFeature({
        id: FEATURE_ID,
        routes: [
            {
                name: ROUTE_NAME,
                path: ROUTE_PATH,
                mount: "svelte",
                load: () => import("./RepositoryServerPage.svelte"),
            },
        ],
    });
}
