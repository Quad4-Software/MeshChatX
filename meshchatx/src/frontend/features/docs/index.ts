// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * In-app MeshChatX guides and Reticulum manual browser.
 */
export function registerDocsFeature(): void {
    registerFeature({
        id: "docs",
        routes: [
            {
                name: "documentation",
                path: "/documentation",
                mount: "svelte",
                load: () => import("./DocsPage.svelte"),
            },
        ],
    });
}
