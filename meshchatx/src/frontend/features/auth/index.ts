// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Register auth feature module
 */
export function registerAuthFeature(): void {
    registerFeature({
        id: "auth",
        routes: [
            {
                name: "auth",
                path: "/auth",
                mount: "svelte",
                load: () => import("./AuthPage.svelte"),
            },
        ],
    });
}
