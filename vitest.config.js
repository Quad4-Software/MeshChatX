import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "path";
import fs from "fs";
import { MICRON_PARSER_GO_RELEASE_TAG } from "./scripts/micron-parser-go-version.mjs";

function isMicronWasmBundledResolved(repoRoot) {
    const wasmDir = path.join(repoRoot, "meshchatx", "src", "frontend", "public", "vendor", "micron-parser-go");
    const wasmFile = path.join(wasmDir, "micron-parser-go.wasm");
    const execFile = path.join(wasmDir, "wasm_exec.js");
    try {
        if (!fs.existsSync(wasmFile) || !fs.existsSync(execFile)) {
            return false;
        }
        return fs.statSync(wasmFile).size >= 8192 && fs.statSync(execFile).size >= 1024;
    } catch {
        return false;
    }
}

const micronWasmBundled = isMicronWasmBundledResolved(__dirname);

function loadMicronWasmIntegrity(repoRoot) {
    if (!micronWasmBundled) return null;
    const integrityPath = path.join(
        repoRoot,
        "meshchatx",
        "src",
        "frontend",
        "public",
        "vendor",
        "micron-parser-go",
        "integrity.json"
    );
    try {
        const content = fs.readFileSync(integrityPath, "utf-8");
        return JSON.parse(content);
    } catch {
        return null;
    }
}

const micronWasmIntegrity = loadMicronWasmIntegrity(__dirname);
const appBuildTimeIso = new Date().toISOString();

export default defineConfig({
    define: {
        __APP_BUILD_TIME__: JSON.stringify(appBuildTimeIso),
        "import.meta.env.VITE_MICRON_WASM_BUNDLED": JSON.stringify(micronWasmBundled ? "true" : "false"),
        "import.meta.env.VITE_MICRON_PARSER_GO_RELEASE": JSON.stringify(MICRON_PARSER_GO_RELEASE_TAG),
        __MICRON_WASM_SRI_WASM__: JSON.stringify(micronWasmIntegrity?.wasm || ""),
        __MICRON_WASM_SRI_EXEC__: JSON.stringify(micronWasmIntegrity?.wasmExec || ""),
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
