// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    flattenLocaleMessages,
    loadPluginLabelMap,
    resolvePluginUiString,
} from "../../meshchatx/src/frontend/js/plugins/pluginLabels.js";

describe("pluginLabels", () => {
    it("flattens nested plugin locale messages", () => {
        const labels = flattenLocaleMessages({
            title: "Mesh Observatory",
            nested: { value: "Hello" },
        });
        expect(labels.title).toBe("Mesh Observatory");
        expect(labels["nested.value"]).toBe("Hello");
    });

    it("resolves plugin UI strings with manifest fallback", () => {
        expect(resolvePluginUiString({}, "title", { name: "Fallback Name" })).toBe("Fallback Name");
        expect(resolvePluginUiString({ title: "From Bundle" }, "title", { name: "Fallback Name" })).toBe(
            "From Bundle"
        );
    });

    it("loads plugin locale messages from plugin assets", async () => {
        const apiClient = {
            async get(url) {
                if (url.includes("/asset/locales/en.json")) {
                    return { data: { title: "Plugin Title" } };
                }
                throw new Error("not found");
            },
        };
        const labels = await loadPluginLabelMap(apiClient, "com.example.plugin", "en", {
            i18n: { directory: "locales", defaultLocale: "en" },
        });
        expect(labels.title).toBe("Plugin Title");
    });
});
