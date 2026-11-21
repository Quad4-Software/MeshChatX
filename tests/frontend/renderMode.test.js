// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolveRenderMode, applyRenderMode } from "../../meshchatx/src/frontend/js/renderMode.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

describe("renderMode flag", () => {
    it("maps the shell software renderMode to the software flag", () => {
        expect(resolveRenderMode({ renderMode: "software" })).toBe("software");
        expect(resolveRenderMode({ renderMode: "hardware" })).toBe("hardware");
        expect(resolveRenderMode({})).toBe("hardware");
        expect(resolveRenderMode(null)).toBe("hardware");
        expect(resolveRenderMode(undefined)).toBe("hardware");
    });

    it("applyRenderMode sets data-render-mode on the root element", () => {
        const root = { dataset: {} };
        expect(applyRenderMode(root, { renderMode: "software" })).toBe("software");
        expect(root.dataset.renderMode).toBe("software");
        expect(applyRenderMode(root, { renderMode: "hardware" })).toBe("hardware");
        expect(root.dataset.renderMode).toBe("hardware");
    });
});

describe("route transition configuration", () => {
    it("App.vue wraps the routed page in an out-in transition", () => {
        const appVue = fs.readFileSync(path.join(ROOT, "meshchatx/src/frontend/components/App.vue"), "utf8");
        // mode out-in serializes leave before enter, so two page roots can
        // never be mounted at once during a route change.
        expect(appVue).toMatch(/<Transition name="route-view-fade" mode="out-in">/);
    });

    it("style.css disables the route fade in software render mode", () => {
        const css = fs.readFileSync(path.join(ROOT, "meshchatx/src/frontend/style.css"), "utf8");
        expect(css).toContain('html[data-render-mode="software"] .route-view-fade-enter-active');
        expect(css).toMatch(/data-render-mode="software"\][\s\S]*?transition: none/);
    });
});
