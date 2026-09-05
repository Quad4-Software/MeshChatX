// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerRNodeFlasherFeature(): void {
    registerFeature({
        id: "rnode-flasher",
        routes: [
            {
                name: "rnode-flasher",
                path: "/tools/rnode-flasher",
                mount: "svelte",
                load: () => import("./RNodeFlasherPage.svelte"),
            },
        ],
    });
}
