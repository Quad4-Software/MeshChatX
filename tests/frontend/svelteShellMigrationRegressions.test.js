// SPDX-License-Identifier: 0BSD

/**
 * Source contracts for APIs that regressed during the Vue→Svelte shell flip.
 * These assert live Svelte sources wire the correct backend paths.
 */

import { readFileSync } from "node:fs";
import { readdirSync, statSync } from "node:fs";
import { resolve, join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");

function src(rel) {
    return readFileSync(resolve(ROOT, rel), "utf8");
}

describe("svelte shell migration API regressions", () => {
    it("map restore starter posts restore-starter", () => {
        const mapService = src("meshchatx/src/frontend/features/map/lib/mapService.ts");
        expect(mapService).toContain("/api/v1/map/mbtiles/restore-starter");
        expect(mapService).not.toContain("/api/v1/map/mbtiles/starter");
    });

    it("settings loads trusted telemetry peers and wires sticker/gif export", () => {
        const settings = src("meshchatx/src/frontend/features/settings/components/SettingsPage.svelte");
        expect(settings).toContain("/api/v1/telemetry/trusted-peers");
        expect(settings).toContain("trusted_peers");
        expect(settings).toContain("onexport={onExportStickers}");
        expect(settings).toContain("onexport={onExportGifs}");
        const actions = src("meshchatx/src/frontend/features/settings/lib/maintenanceActions.ts");
        expect(actions).toContain("/api/v1/stickers/export");
        expect(actions).toContain("/api/v1/gifs/export");
        expect(actions).toContain("/api/v1/stickers/import");
        expect(actions).toContain("/api/v1/gifs/import");
    });

    it("relay clears active room on leave and persists hub order", () => {
        const page = src("meshchatx/src/frontend/features/relay-chat/components/RelayChatPage.svelte");
        expect(page).toContain("/api/v1/rrc/active/clear");
        expect(page).toContain("/api/v1/rrc/hubs/order");
        expect(page).toContain("onreorderhubs={onReorderHubs}");
    });

    it("boot uses svelte-i18n and live App.svelte without vue-i18n createI18n", () => {
        const main = src("meshchatx/src/frontend/main.ts");
        expect(main).toContain("initSvelteI18n");
        expect(main).toContain("features/app-shell/App.svelte");
        expect(main).toContain("getCurrentUiLocale");
        expect(main).not.toContain('from "vue-i18n"');
        expect(main).not.toContain("configureVueIslands");
        expect(main).not.toContain("i18n.global.locale");
    });

    it("plugin routes register via hashRouter featureLoad only", () => {
        const host = src("meshchatx/src/frontend/js/plugins/PluginHost.ts");
        expect(host).toContain("featureLoad:");
        expect(host).not.toContain("FeaturePageHost.vue");
    });

    it("frontend tree has no remaining .vue sources", () => {
        const root = resolve(ROOT, "meshchatx/src/frontend");
        const vueFiles = [];
        function walk(dir) {
            for (const name of readdirSync(dir)) {
                const p = join(dir, name);
                if (statSync(p).isDirectory()) walk(p);
                else if (name.endsWith(".vue")) vueFiles.push(p);
            }
        }
        walk(root);
        expect(vueFiles).toEqual([]);
    });
});
