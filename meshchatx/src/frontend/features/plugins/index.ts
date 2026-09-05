// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerPluginsFeature(): void {
    registerFeature({
        id: "plugins",
        routes: [
            {
                name: "plugin-mcx-bugs",
                path: "/plugins/com.meshchatx.mcx-bugs",
                mount: "svelte",
                load: () => import("./PluginPage.svelte"),
                routeProps: { pluginId: "com.meshchatx.mcx-bugs" },
            },
            {
                name: "plugin-view",
                path: "/plugins/:pluginId",
                mount: "svelte",
                load: () => import("./PluginPage.svelte"),
            },
        ],
    });
}
