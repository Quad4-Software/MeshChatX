// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("Locale and theme regressions (source contracts)", () => {
    it("updateConfig and onLanguageChange persist language through PATCH helpers", () => {
        const config = src("meshchatx/src/frontend/features/app-shell/lib/appShellConfig.ts");
        expect(config).toContain("export async function updateConfig");
        expect(config).toContain("patchServerConfig");
        expect(config).toContain("export async function onLanguageChange");
        expect(config).toContain("setLocale(");
        expect(config).toContain("normalizeUiLocaleCode");
    });

    it("boot theme clears html.dark for light", () => {
        const boot = src("meshchatx/src/frontend/public/boot-theme.js");
        expect(boot).toContain('classList.remove("dark")');
    });
});
