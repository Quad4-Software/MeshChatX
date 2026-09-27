// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    validatePluginManifest,
    manifestPermissionSummary,
} from "../../meshchatx/src/frontend/js/plugins/pluginManifest.js";
import { declaredPermissionIds, permissionLabel } from "../../meshchatx/src/frontend/js/plugins/pluginPermissions.js";

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

    it("summarizes permissions with labels", () => {
        const lines = manifestPermissionSummary(
            {
                permissions: {
                    hooks: ["announce.received"],
                    managers: ["destinationPath.read"],
                    storage: "isolated",
                    network: "fetch",
                },
            },
            (key) => (key === "plugins.permissions.network.fetch" ? "Make outbound internet HTTP requests" : key)
        );
        expect(lines.join(" ")).toContain("hooks:announce.received");
        expect(lines.join(" ")).toContain("Make outbound internet HTTP requests");
    });

    it("builds declared permission ids including network.fetch", () => {
        const ids = declaredPermissionIds({
            permissions: {
                hooks: ["rns.link.event"],
                network: "http",
            },
        });
        expect(ids).toContain("hooks:rns.link.event");
        expect(ids).toContain("network:fetch");
    });

    it("labels unknown permissions with the raw id", () => {
        expect(permissionLabel("custom:thing", (key) => key)).toBe("custom:thing");
    });

    it("accepts backend.type python", () => {
        const manifest = validatePluginManifest({
            id: "com.example.python",
            version: "1.0.0",
            apiVersion: 1,
            backend: { entry: "backend/main.py", type: "python" },
        });
        expect(manifest.backend.type).toBe("python");
    });
});
