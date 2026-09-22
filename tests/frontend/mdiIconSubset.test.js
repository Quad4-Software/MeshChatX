// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import {
    collectLiteralIconNames,
    resolveMdiExportKey,
    CURATED_EXTRA_ICON_NAMES,
} from "../../scripts/build/mdi-icon-scan.mjs";
import { getMdiIconPath, isValidMdiIconName, resolveMdiIconKey, buildMdiIconNames } from "@/js/mdiIconNames.js";
import { MDI_USED_PATHS } from "@/js/generated/mdiIconData.js";

const require = createRequire(import.meta.url);
const mdi = require("@mdi/js");
const frontendRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    "..",
    "meshchatx",
    "src",
    "frontend"
);

describe("mdi icon subset coverage", () => {
    it("covers every literal icon name referenced in frontend source", () => {
        const literals = collectLiteralIconNames(frontendRoot);
        const missing = [];
        for (const name of literals) {
            const key = resolveMdiExportKey(name, mdi);
            // Names that do not exist in @mdi/js fall back at runtime today
            // as well; only real icons must be present in the subset.
            if (key && !MDI_USED_PATHS[key]) {
                missing.push(`${name} (${key})`);
            }
        }
        expect(missing, "literal icon names missing from generated subset; run: pnpm run generate:mdi-icons").toEqual(
            []
        );
    });

    it("covers curated dynamic icon names", () => {
        for (const name of CURATED_EXTRA_ICON_NAMES) {
            const key = resolveMdiExportKey(name, mdi);
            expect(key, `curated icon ${name} no longer exists in @mdi/js`).toBeTruthy();
            expect(MDI_USED_PATHS[key], `curated icon ${name} missing path data`).toBeTruthy();
        }
    });
});

describe("mdiIconNames subset resolution", () => {
    it("returns identical names as the full @mdi/js export list", () => {
        const expected = Object.keys(mdi)
            .map((k) =>
                k
                    .replace(/^mdi/, "")
                    .replace(/([a-z])([A-Z])/g, "$1-$2")
                    .toLowerCase()
            )
            .sort();
        expect([...buildMdiIconNames()].sort()).toEqual(expected);
    });

    it("resolves a used literal icon path synchronously", () => {
        expect(getMdiIconPath("close")).toBe(mdi.mdiClose);
        expect(getMdiIconPath("loading")).toBe(mdi.mdiLoading);
    });

    it("returns a non-empty fallback for unknown names without throwing", () => {
        expect(getMdiIconPath("definitely-not-an-icon-name-xyz")).toBeTruthy();
        expect(getMdiIconPath("")).toBeTruthy();
        expect(getMdiIconPath(null)).toBeTruthy();
    });

    it("keeps validation semantics for exact names", () => {
        expect(isValidMdiIconName("account")).toBe(true);
        expect(isValidMdiIconName("account-outline")).toBe(true);
        expect(isValidMdiIconName("not-a-real-mdi-icon")).toBe(false);
        expect(isValidMdiIconName("../etc/passwd")).toBe(false);
        expect(resolveMdiIconKey("account")).toBe("mdiAccount");
        expect(resolveMdiIconKey("mdiRoutes")).toBe("mdiRoutes");
        expect(resolveMdiIconKey("mdiRoute")).toBe("mdiRoutes");
    });
});
