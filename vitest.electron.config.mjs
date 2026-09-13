import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        globals: true,
        environment: "node",
        // Same vitest-worker teardown race as vitest.config.mjs: ignore
        // pending console-log RPC rejections at worker shutdown.
        onUnhandledError(error) {
            const message = error && error.message ? String(error.message) : String(error);
            if (message.includes("Closing rpc while")) {
                return false;
            }
        },
        include: ["tests/electron/**/*.test.js"],
        coverage: {
            provider: "v8",
            reporter: ["text", "json-summary"],
            reportsDirectory: "./coverage-electron",
            include: ["electron/**/*.js"],
            exclude: ["electron/assets/**"],
        },
    },
});
