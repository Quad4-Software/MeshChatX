// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerAboutFeature(): void {
    registerFeature({
        id: "about",
        routes: [
            {
                name: "about",
                path: "/about",
                mount: "svelte",
                load: () => import("./AboutPage.svelte"),
            },
        ],
    });
}
