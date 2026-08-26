// SPDX-License-Identifier: 0BSD

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");
const FRONTEND_ROOT = join(ROOT, "meshchatx", "src", "frontend");

function readRepo(relPath) {
    return readFileSync(resolve(ROOT, relPath), "utf8");
}

function walkVueFiles(dir, out = []) {
    for (const name of readdirSync(dir)) {
        const filePath = join(dir, name);
        const stat = statSync(filePath);
        if (stat.isDirectory()) {
            walkVueFiles(filePath, out);
            continue;
        }
        if (name.endsWith(".vue")) {
            out.push(filePath);
        }
    }
    return out;
}

describe("frontend stack migration oracle", () => {
    it("package.json no longer depends on Vuetify or @mdi/font", () => {
        const pkg = JSON.parse(readRepo("package.json"));
        const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };
        expect(allDeps.vuetify).toBeUndefined();
        expect(allDeps["vite-plugin-vuetify"]).toBeUndefined();
        expect(allDeps["@mdi/font"]).toBeUndefined();
        expect(allDeps["@mdi/js"]).toBeTruthy();
    });

    it("vite.config.js uses Vite 8 features and excludes Vuetify bundling", () => {
        const vite = readRepo("vite.config.js");
        expect(vite).toContain("rolldownOptions");
        expect(vite).toContain("chunkImportMap: false");
        expect(vite).toContain("tsconfigPaths: true");
        expect(vite).toContain("MESHCHAT_VITE_BUNDLED_DEV");
        expect(vite).not.toContain("vite-plugin-vuetify");
        expect(vite).not.toContain("vendor-vuetify");
    });

    it("main.js bootstraps Vue without Vuetify or MDI font CSS", () => {
        const main = readRepo("meshchatx/src/frontend/main.js");
        expect(main).not.toContain("createVuetify");
        expect(main).not.toContain("@mdi/font");
        expect(main).not.toContain(".use(vuetify)");
    });

    it("Vue SFCs do not reference Vuetify components or v-icon", () => {
        const vueFiles = walkVueFiles(FRONTEND_ROOT);
        const offenders = [];
        for (const file of vueFiles) {
            const body = readFileSync(file, "utf8");
            if (
                /<v-(?!if|else-if|else|for|model|show|bind|on|slot|memo|html|click-outside)[a-z-]/.test(body) ||
                body.includes('from "vuetify')
            ) {
                offenders.push(file.replace(`${ROOT}/`, ""));
            }
        }
        expect(offenders).toEqual([]);
    });

    it("theme engine no longer syncs Vuetify theme colors", () => {
        const theme = readRepo("meshchatx/src/frontend/theme/themeEngine.js");
        expect(theme).not.toContain("syncVuetifyThemeColors");
        expect(theme).not.toContain("vuetifyTheme");
        const tokens = readRepo("meshchatx/src/frontend/theme/designTokens.js");
        expect(tokens).not.toContain("vuetifyThemesFromTokens");
    });

    it("shared modal and popover components exist for Vuetify replacements", () => {
        expect(readRepo("meshchatx/src/frontend/components/AppModal.vue")).toContain("AppModal");
        expect(readRepo("meshchatx/src/frontend/components/ClickPopover.vue")).toContain("ClickPopover");
    });
});
