// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerSettingsFeature(): void {
    registerFeature({
        id: "settings",
        routes: [
            {
                name: "settings",
                path: "/settings",
                mount: "svelte",
                load: () => import("./components/SettingsPage.svelte"),
            },
            {
                name: "identities",
                path: "/identities",
                mount: "svelte",
                load: () => import("./components/IdentitiesPage.svelte"),
            },
        ],
    });
}
