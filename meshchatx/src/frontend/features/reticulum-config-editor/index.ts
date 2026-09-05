// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";
import {
    RETICULUM_CONFIG_EDITOR_FEATURE_ID,
    RETICULUM_CONFIG_EDITOR_ROUTE_NAME,
    RETICULUM_CONFIG_EDITOR_ROUTE_PATH,
} from "./lib/constants.js";

/**
 * Reticulum config raw editor UI.
 */
export function registerReticulumConfigEditorFeature(): void {
    registerFeature({
        id: RETICULUM_CONFIG_EDITOR_FEATURE_ID,
        routes: [
            {
                name: RETICULUM_CONFIG_EDITOR_ROUTE_NAME,
                path: RETICULUM_CONFIG_EDITOR_ROUTE_PATH,
                mount: "svelte",
                load: () => import("./ReticulumConfigEditorPage.svelte"),
            },
        ],
    });
}
