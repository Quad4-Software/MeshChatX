// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Micron markup visual and code editor for Nomad Network and Reticulum pages.
 */
export function registerMicronEditorFeature(): void {
    registerFeature({
        id: "micron-editor",
        routes: [
            {
                name: "micron-editor",
                path: "/micron-editor",
                mount: "svelte",
                load: () => import("./MicronEditorPage.svelte"),
            },
        ],
    });
}
