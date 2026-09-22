// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";
import { PAPER_MESSAGE_TOOL_ROUTE_NAME, PAPER_MESSAGE_TOOL_ROUTE_PATH } from "./lib/constants.js";

/**
 * Register paper message feature
 */
export function registerPaperMessageFeature(): void {
    registerFeature({
        id: "paper-message",
        routes: [
            {
                name: PAPER_MESSAGE_TOOL_ROUTE_NAME,
                path: PAPER_MESSAGE_TOOL_ROUTE_PATH,
                mount: "svelte",
                load: () => import("./PaperMessagePage.svelte"),
            },
        ],
    });
}
