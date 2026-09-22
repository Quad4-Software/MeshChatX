import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import path from "path";
import fs from "fs";
import { MICRON_PARSER_GO_RELEASE_TAG } from "./scripts/micron-parser-go-version.mjs";

// Persist Node's on-disk compile cache between runs; Vitest propagates the
// variable to every worker. node_modules is already gitignored.
process.env.NODE_COMPILE_CACHE ??= "node_modules/.cache/node-compile-cache";

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

const micronWasmBundled = isMicronWasmBundledResolved(import.meta.dirname);

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

const micronWasmIntegrity = loadMicronWasmIntegrity(import.meta.dirname);
const appBuildTimeIso = new Date().toISOString();

// These files stub window/location by replacing the whole global, which is
// impossible inside a vmThreads realm where window is a getter-only VM global.
// They run on the default forks pool in a dedicated project.
const WINDOW_REPLACING_TESTS = [
    "tests/frontend/apiClientCsrfRecovery.test.js",
    "tests/frontend/apiClientMutationTimeout.test.js",
    "tests/frontend/AuthPage.test.js",
    "tests/frontend/BergamotBacking.test.js",
    "tests/frontend/FatalErrorPage.test.js",
    "tests/frontend/IdentitiesPage.test.js",
    "tests/frontend/identitySwitchUiContracts.test.js",
    "tests/frontend/WebSocketConnection.test.js",
];

export default defineConfig({
    define: {
        __APP_BUILD_TIME__: JSON.stringify(appBuildTimeIso),
        "import.meta.env.VITE_MICRON_WASM_BUNDLED": JSON.stringify(micronWasmBundled ? "true" : "false"),
        "import.meta.env.VITE_MICRON_PARSER_GO_RELEASE": JSON.stringify(MICRON_PARSER_GO_RELEASE_TAG),
        __MICRON_WASM_SRI_WASM__: JSON.stringify(micronWasmIntegrity?.wasm || ""),
        __MICRON_WASM_SRI_EXEC__: JSON.stringify(micronWasmIntegrity?.wasmExec || ""),
    },
    plugins: [svelte()],
    test: {
        execArgv: [
            "--no-experimental-webstorage",
            "--require",
            path.resolve(import.meta.dirname, "tests/frontend/patch-console.cjs"),
        ],
        testTimeout: 20000,
        hookTimeout: 20000,
        teardownTimeout: 30000,
        globals: true,
        environment: "jsdom",
        // Persist the transform cache between runs so unchanged modules are
        // not re-transformed on every invocation.
        fsModuleCache: true,
        // vitest-worker teardown race: a console log RPC still in flight
        // when the worker closes surfaces as an unhandled rejection even
        // though every test passed. Ignore only that specific race.
        onUnhandledError(error) {
            const message = error && error.message ? String(error.message) : String(error);
            if (message.includes("Closing rpc while")) {
                return false;
            }
        },
        setupFiles: ["tests/frontend/setup.js"],
        // vmThreads creates the jsdom environment once per worker instead of
        // once per file while still giving every file a fresh window. With
        // 300+ test files this removes most of the environment phase cost.
        // Files that replace the window or location globals outright cannot
        // run in a VM realm, so they stay on the forks pool.
        projects: [
            {
                extends: true,
                test: {
                    name: "dom",
                    pool: "vmThreads",
                    include: ["tests/frontend/**/*.{test,spec}.{js,ts,jsx,tsx}"],
                    exclude: [
                        "tests/frontend/browser/**",
                        "**/*.browser.test.*",
                        "**/*.browser.spec.*",
                        ...WINDOW_REPLACING_TESTS,
                    ],
                },
            },
            {
                extends: true,
                test: {
                    name: "dom-forks",
                    pool: "forks",
                    include: WINDOW_REPLACING_TESTS,
                },
            },
        ],
        ui: false,
        open: false,
        coverage: {
            provider: "v8",
            reporter: ["text", "json-summary"],
            reportsDirectory: "./coverage",
            include: ["meshchatx/src/frontend/**/*.{js,ts,svelte}"],
            exclude: [
                "meshchatx/src/frontend/**/*.d.ts",
                "meshchatx/src/frontend/public/**",
                "meshchatx/src/frontend/locales/**",
                "**/node_modules/**",
            ],
        },
    },
    resolve: {
        dedupe: ["svelte"],
        conditions: ["browser"],
        tsconfigPaths: true,
        alias: {
            "@": path.resolve(import.meta.dirname, "meshchatx", "src", "frontend"),
        },
    },
});
