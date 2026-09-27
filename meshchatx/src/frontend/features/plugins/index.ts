// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerPluginsFeature(): void {
    registerFeature({
        id: "plugins",
        routes: [
            {
                name: "plugin-mcx-hello",
                path: "/plugins/com.meshchatx.mcx-hello",
                mount: "svelte",
                load: () => import("./PluginPage.svelte"),
                routeProps: { pluginId: "com.meshchatx.mcx-hello" },
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
