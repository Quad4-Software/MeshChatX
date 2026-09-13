// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("UI theme and visibility shell contracts", () => {
    it("app shell applies theme from config helpers", () => {
        const config = src("meshchatx/src/frontend/features/app-shell/lib/appShellConfig.ts");
        const toggle = src("meshchatx/src/frontend/ui/svelte/Toggle.svelte");
        const language = src("meshchatx/src/frontend/ui/svelte/LanguageSelector.svelte");
        expect(config).toContain("applyShellAppearance");
        expect(config).toContain("toggleTheme");
        expect(config).toContain("onLanguageChange");
        expect(toggle).toContain("checked");
        expect(language).toContain("setLocale");
    });
});
