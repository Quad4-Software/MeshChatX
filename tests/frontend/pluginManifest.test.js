// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { validatePluginManifest, manifestPermissionSummary } from "../../meshchatx/src/frontend/js/plugins/pluginManifest.js";

describe("pluginManifest", () => {
    it("validates a minimal manifest", () => {
        const manifest = validatePluginManifest({
            id: "com.example.demo",
            version: "1.0.0",
            apiVersion: 1,
            frontend: { entry: "frontend/main.js", type: "js" },
        });
        expect(manifest.id).toBe("com.example.demo");
    });

    it("rejects unsupported api versions", () => {
        expect(() =>
            validatePluginManifest({
                id: "com.example.demo",
                version: "1.0.0",
                apiVersion: 99,
            })
        ).toThrow(/apiVersion/);
    });

    it("summarizes permissions", () => {
        const lines = manifestPermissionSummary({
            permissions: {
                hooks: ["announce.received"],
                managers: ["destinationPath.read"],
                storage: "isolated",
            },
        });
        expect(lines.join(" ")).toContain("announce.received");
        expect(lines.join(" ")).toContain("destinationPath.read");
    });
});
