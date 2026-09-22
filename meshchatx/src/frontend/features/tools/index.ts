// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerToolsFeature(): void {
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
