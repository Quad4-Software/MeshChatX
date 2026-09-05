// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * NomadNet page archives feature registration
 */
export function registerArchivesFeature(): void {
    registerFeature({
        id: "archives",
        routes: [
            {
                name: "archives",
                path: "/archives",
                mount: "svelte",
                load: () => import("./ArchivesPage.svelte"),
            },
        ],
    });
}
