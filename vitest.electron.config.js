import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        globals: true,
        environment: "node",
        include: ["tests/electron/**/*.test.js"],
        coverage: {
            provider: "v8",
            reporter: ["text", "json-summary"],
            reportsDirectory: "./coverage-electron",
            include: ["electron/**/*.js"],
            exclude: ["electron/assets/**", "electron/main-legacy.js"],
        },
    },
});
