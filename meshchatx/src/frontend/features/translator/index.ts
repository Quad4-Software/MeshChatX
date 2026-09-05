// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Text translation UI using Argos Translate or LibreTranslate.
 */
export function registerTranslatorFeature(): void {
    registerFeature({
        id: "translator",
        routes: [
            {
                name: "translator",
                path: "/translator",
                mount: "svelte",
                load: () => import("./TranslatorPage.svelte"),
            },
        ],
    });
}
