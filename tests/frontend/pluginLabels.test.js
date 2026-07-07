// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { buildPluginLabelMap } from "../../meshchatx/src/frontend/js/plugins/pluginLabels.js";

describe("pluginLabels", () => {
    it("builds flat plugin label map from translate function", () => {
        const labels = buildPluginLabelMap((key) => {
            if (key === "plugins.transport_node_monitor.title") {
                return "Transport Node Monitor";
            }
            return key;
        });
        expect(labels["plugins.transport_node_monitor.title"]).toBe("Transport Node Monitor");
    });
});
