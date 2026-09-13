// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Reticulum network probe feature registration
 */
export function registerRnprobeFeature(): void {
    registerFeature({
        id: "rnprobe",
        routes: [
            {
                name: "rnprobe",
                path: "/rnprobe",
                mount: "svelte",
                load: () => import("./RNProbePage.svelte"),
            },
        ],
    });
}
