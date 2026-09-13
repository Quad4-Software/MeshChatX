// SPDX-License-Identifier: 0BSD
import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { playwright } from "@vitest/browser-playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
    plugins: [svelte()],
    test: {
        globals: true,
        include: ["tests/frontend/browser/**/*.{test,spec}.{js,ts}"],
        setupFiles: ["tests/frontend/browser/setup.js"],
        browser: {
            enabled: true,
            provider: playwright(),
            instances: [{ browser: "chromium", headless: true }],
        },
    },
    resolve: {
        dedupe: ["svelte"],
        conditions: ["browser"],
        alias: {
            "@": path.resolve(rootDir, "meshchatx", "src", "frontend"),
        },
    },
});
