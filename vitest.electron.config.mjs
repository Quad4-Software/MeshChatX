import { defineConfig } from "vitest/config";

process.env.NODE_COMPILE_CACHE ??= "node_modules/.cache/node-compile-cache";

export default defineConfig({
    test: {
        globals: true,
        environment: "node",
        fsModuleCache: true,
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
            reportOnFailure: true,
            // Ratchet: floor just under current totals (lines 47.6,
            // stmts 47.6, funcs 48.5, branches 46.0).
            thresholds: {
                lines: 47,
                statements: 47,
                functions: 48,
                branches: 45,
            },
            include: ["electron/**/*.js"],
            exclude: ["electron/assets/**"],
        },
    },
});
