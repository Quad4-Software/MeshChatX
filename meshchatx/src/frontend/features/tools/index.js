// SPDX-License-Identifier: 0BSD AND MIT

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerToolsFeature() {
    registerFeature({
        id: "tools",
        routes: [
            {
                name: "tools",
                path: "/tools",
                mount: "svelte",
                load: () => import("./ToolsPage.svelte"),
            },
        ],
    });
}
