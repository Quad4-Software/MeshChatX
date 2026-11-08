import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");

describe("desktop bridge sync", () => {
    it("committed public copy matches the canonical shell bridge", () => {
        const canonical = readFileSync(resolve(root, "desktop/shell/desktop-bridge.js"), "utf8");
        const committed = readFileSync(resolve(root, "meshchatx/src/frontend/public/desktop-bridge.js"), "utf8");
        expect(committed).toBe(canonical);
    });

    it("index.html loads the bridge before the app module", () => {
        const html = readFileSync(resolve(root, "meshchatx/src/frontend/index.html"), "utf8");
        const bridgeIdx = html.indexOf("desktop-bridge.js");
        const moduleIdx = html.indexOf('type="module"');
        expect(bridgeIdx).toBeGreaterThan(-1);
        expect(moduleIdx).toBeGreaterThan(-1);
        expect(bridgeIdx).toBeLessThan(moduleIdx);
    });
});
