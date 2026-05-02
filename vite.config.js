import path from "path";
import fs from "fs";
import { defineConfig } from "vite";
import { MICRON_PARSER_GO_RELEASE_TAG } from "./scripts/micron-parser-go-version.mjs";
import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import vuetify from "vite-plugin-vuetify";

const vendorChunkGroups = [
    { test: /[/\\]node_modules[/\\]vuetify/, name: "vendor-vuetify", priority: 100 },
    { test: /[/\\]node_modules[/\\](vis-network|vis-data)/, name: "vendor-vis", priority: 95 },
    { test: /[/\\]node_modules[/\\]vue-router/, name: "vendor-vue-router", priority: 90 },
    { test: /[/\\]node_modules[/\\](protobufjs|@protobufjs)/, name: "vendor-protobuf", priority: 85 },
    { test: /[/\\]node_modules[/\\]dayjs/, name: "vendor-dayjs", priority: 80 },
    { test: /[/\\]node_modules[/\\]@mdi(?:\/|\\)js/, name: "vendor-mdi", priority: 75 },
    { test: /[/\\]node_modules[/\\]compressorjs/, name: "vendor-compressor", priority: 70 },
    { test: /[/\\]node_modules[/\\]click-outside-vue3/, name: "vendor-click-outside", priority: 65 },
    { test: /[/\\]node_modules[/\\]mitt/, name: "vendor-mitt", priority: 60 },
    { test: /[/\\]node_modules[/\\]micron-parser/, name: "vendor-micron", priority: 55 },
    { test: /MicronParser\.js/, name: "vendor-micron", priority: 55 },
    { test: /[/\\]node_modules[/\\]electron-prompt/, name: "vendor-electron-prompt", priority: 50 },
    { test: /[/\\]node_modules[/\\].*vue/, name: "vendor-vue", priority: 45 },
    { test: /[/\\]node_modules[/\\]/, name: "vendor-other", priority: 10 },
];

// Purge old assets before build to prevent accumulation
const assetsDir = path.join(__dirname, "meshchatx", "public", "assets");
if (fs.existsSync(assetsDir)) {
    fs.rmSync(assetsDir, { recursive: true, force: true });
}

const e2eBackendPort = process.env.E2E_BACKEND_PORT || "8000";
const e2eBackendOrigin = `http://127.0.0.1:${e2eBackendPort}`;
const e2eBackendWs = `ws://127.0.0.1:${e2eBackendPort}`;

const appBuildTimeIso = new Date().toISOString();

function isMicronWasmBundledResolved() {
    const wasmDir = path.join(__dirname, "meshchatx", "src", "frontend", "public", "vendor", "micron-parser-go");
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

const micronWasmBundled = isMicronWasmBundledResolved();

function loadMicronWasmIntegrity() {
    if (!micronWasmBundled) return null;
    const integrityPath = path.join(
        __dirname,
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
        console.warn("vite: could not load micron-parser-go integrity.json");
        return null;
    }
}

const micronWasmIntegrity = loadMicronWasmIntegrity();

export default defineConfig({
    define: {
        __APP_BUILD_TIME__: JSON.stringify(appBuildTimeIso),
        "import.meta.env.VITE_MICRON_WASM_BUNDLED": JSON.stringify(micronWasmBundled ? "true" : "false"),
        "import.meta.env.VITE_MICRON_PARSER_GO_RELEASE": JSON.stringify(MICRON_PARSER_GO_RELEASE_TAG),
        __MICRON_WASM_SRI_WASM__: JSON.stringify(micronWasmIntegrity?.wasm || ""),
        __MICRON_WASM_SRI_EXEC__: JSON.stringify(micronWasmIntegrity?.wasmExec || ""),
    },
    plugins: [
        tailwindcss(),
        vue({
            template: {
                compilerOptions: {
                    isCustomElement: (tag) => tag === "emoji-picker",
                },
            },
        }),
        vuetify(),
    ],

    server: {
        port: 5173,
        proxy: {
            "/api": { target: e2eBackendOrigin, changeOrigin: true },
            "/ws": { target: e2eBackendWs, ws: true },
            "/ws/telephone/audio": { target: e2eBackendWs, ws: true },
        },
    },

    // vite app is loaded from /meshchatx/src/frontend
    root: path.join(__dirname, "meshchatx", "src", "frontend"),

    publicDir: path.join(__dirname, "meshchatx", "src", "frontend", "public"),

    build: {
        sourcemap: false,
        // @mdi/js and other vendor chunks exceed 700 kB minified; splitting icons further is a larger refactor.
        chunkSizeWarningLimit: 3500,
        minify: "terser",
        terserOptions: {
            compress: {
                drop_console: false,
                pure_funcs: ["console.debug"],
            },
        },

        // we want to compile vite app to meshchatx/public which is bundled and served by the python executable
        outDir: path.join(__dirname, "meshchatx", "public"),
        emptyOutDir: false,

        rolldownOptions: {
            checks: {
                pluginTimings: false,
            },
            treeshake: {
                moduleSideEffects: (id) => {
                    if (id.includes("@mdi/js")) {
                        return false;
                    }
                    return null;
                },
            },
            input: {
                app: path.join(__dirname, "meshchatx", "src", "frontend", "index.html"),
            },
            output: {
                codeSplitting: {
                    minSize: 20_000,
                    groups: [
                        ...vendorChunkGroups,
                        {
                            name: "shared-async",
                            minShareCount: 2,
                            minSize: 10_000,
                            priority: 5,
                        },
                    ],
                },
            },
        },
    },

    optimizeDeps: {
        include: ["dayjs", "vue", "emoji-picker-element"],
    },

    resolve: {
        dedupe: ["vue"],
        alias: {
            "micron-parser": path.join(__dirname, "node_modules", "micron-parser", "js", "micron-parser.js"),
        },
    },
});
