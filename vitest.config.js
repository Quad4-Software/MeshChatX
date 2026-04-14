import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "path";

const appBuildTimeIso = new Date().toISOString();

export default defineConfig({
    define: {
        __APP_BUILD_TIME__: JSON.stringify(appBuildTimeIso),
    },
    plugins: [
        vue({
            template: {
                compilerOptions: {
                    isCustomElement: (tag) => tag === "emoji-picker",
                },
            },
        }),
    ],
    test: {
        execArgv: [
            "--no-experimental-webstorage",
            "--require",
            path.resolve(__dirname, "tests/frontend/patch-console.cjs"),
        ],
        globals: true,
        environment: "jsdom",
        include: ["tests/frontend/**/*.{test,spec}.{js,ts,jsx,tsx}"],
        setupFiles: ["tests/frontend/setup.js"],
        ui: false,
        open: false,
        coverage: {
            provider: "v8",
            reporter: ["text", "json-summary"],
            reportsDirectory: "./coverage",
            include: ["meshchatx/src/frontend/**/*.{js,vue}"],
            exclude: [
                "meshchatx/src/frontend/**/*.d.ts",
                "meshchatx/src/frontend/public/**",
                "meshchatx/src/frontend/locales/**",
                "**/node_modules/**",
            ],
        },
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "meshchatx", "src", "frontend"),
            "micron-parser": path.resolve(__dirname, "node_modules", "micron-parser", "js", "micron-parser.js"),
        },
    },
});
