// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * App shell feature: routes the shell owns rather than a page module.
 * Changelog was registered inline in main.ts under vue-router.
 */
export function registerAppShellFeature(): void {
    registerFeature({
        id: "app-shell",
        routes: [
            {
                name: "changelog",
                path: "/changelog",
                mount: "svelte",
                load: () => import("./ChangelogPage.svelte"),
                meta: { isPage: true },
            },
        ],
    });
}
