// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerDebugLogsFeature() {
    registerFeature({
        id: "debug-logs",
        routes: [
            {
                name: "debug-logs",
                path: "/debug/logs",
                mount: "svelte",
                load: () => import("./DebugLogsPage.svelte"),
            },
        ],
    });
}
