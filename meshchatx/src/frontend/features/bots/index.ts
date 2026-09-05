// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerBotsFeature(): void {
    registerFeature({
        id: "bots",
        routes: [
            {
                name: "bots",
                path: "/bots",
                mount: "svelte",
                load: () => import("./BotsPage.svelte"),
            },
        ],
    });
}
