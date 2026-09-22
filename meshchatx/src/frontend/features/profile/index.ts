// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerProfileFeature(): void {
    registerFeature({
        id: "profile",
        routes: [
            {
                name: "profile.icon",
                path: "/profile/icon",
                mount: "svelte",
                load: () => import("./ProfileIconPage.svelte"),
            },
        ],
    });
}
