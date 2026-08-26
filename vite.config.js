import path from "path";
import fs from "fs";
import { defineConfig } from "vite";
import { MICRON_PARSER_GO_RELEASE_TAG } from "./scripts/micron-parser-go-version.mjs";
import { meshchatxServiceWorkerPlugin } from "./scripts/build/generate_service_worker.mjs";
import { detectLaunchEditor, isVueDevToolsEnabled } from "./scripts/vite-dx.mjs";
import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import vueDevTools from "vite-plugin-vue-devtools";
const vendorChunkGroups = [
    { test: /[/\\]node_modules[/\\](vis-network|vis-data)/, name: "vendor-vis", priority: 95 },
    { test: /[/\\]node_modules[/\\]vue-router/, name: "vendor-vue-router", priority: 90 },
    { test: /[/\\]node_modules[/\\](protobufjs|@protobufjs)/, name: "vendor-protobuf", priority: 85 },
    { test: /[/\\]node_modules[/\\]@mdi(?:\/|\\)js/, name: "vendor-mdi", priority: 75 },
    { test: /[/\\]node_modules[/\\]compressorjs/, name: "vendor-compressor", priority: 70 },
    { test: /[/\\]node_modules[/\\]micron-parser/, name: "vendor-micron", priority: 55 },
    { test: /MicronParser\.js/, name: "vendor-micron", priority: 55 },
    { test: /[/\\]node_modules[/\\]electron-prompt/, name: "vendor-electron-prompt", priority: 50 },
    { test: /[/\\]node_modules[/\\].*vue/, name: "vendor-vue", priority: 45 },
    { test: /[/\\]node_modules[/\\]/, name: "vendor-other", priority: 10 },
];

const assetsDir = path.join(__dirname, "meshchatx", "public", "assets");

const e2eBackendPort = process.env.E2E_BACKEND_PORT || "8000";

function envBool(value) {
    if (value === undefined || value === null || value === "") {
        return false;
    }
    return ["1", "true", "yes"].includes(String(value).toLowerCase());
}

const backendUsesHttps = !envBool(process.env.MESHCHAT_NO_HTTPS);
const e2eBackendOrigin = backendUsesHttps
    ? `https://127.0.0.1:${e2eBackendPort}`
    : `http://127.0.0.1:${e2eBackendPort}`;
// http-proxy expects an http(s) target for WS upgrades (ws: true). Using wss://
// here has caused noisy write EPIPE / reconnect loops under Vite 8.
const backendProxyTls = backendUsesHttps ? { secure: false } : {};

/**
 * Attach quiet handlers for expected proxy disconnects (browser refresh,
 * client reconnect, peer closed before proxy flush).
 * @param {import('http-proxy').Server} proxy
 */
function configureQuietProxyErrors(proxy) {
    proxy.on("error", (err, _req, res) => {
        const code = err && err.code;
        if (code === "EPIPE" || code === "ECONNRESET" || code === "ECONNREFUSED") {
            if (res && !res.headersSent && typeof res.writeHead === "function") {
                try {
                    res.writeHead(502);
                    res.end("Bad gateway");
                } catch {
                    /* already closed */
                }
            }
            return;
        }
        console.error("[vite] proxy error:", err);
    });
    proxy.on("proxyReqWs", (_proxyReq, _req, socket) => {
        socket.on("error", (err) => {
            const code = err && err.code;
            if (code === "EPIPE" || code === "ECONNRESET") {
                return;
            }
            console.error("[vite] ws proxy socket error:", err);
        });
    });
}

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

function isVisualiserWasmBundledResolved() {
    const wasmDir = path.join(__dirname, "meshchatx", "src", "frontend", "public", "vendor", "visualiser-wasm");
    const wasmFile = path.join(wasmDir, "visualiser.wasm");
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
const visualiserWasmBundled = isVisualiserWasmBundledResolved();

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

function loadVisualiserWasmIntegrity() {
    if (!visualiserWasmBundled) return null;
    const integrityPath = path.join(
        __dirname,
        "meshchatx",
        "src",
        "frontend",
        "public",
        "vendor",
        "visualiser-wasm",
        "integrity.json"
    );
    try {
        return JSON.parse(fs.readFileSync(integrityPath, "utf-8"));
    } catch {
        console.warn("vite: could not load visualiser-wasm integrity.json");
        return null;
    }
}

const micronWasmIntegrity = loadMicronWasmIntegrity();
const visualiserWasmIntegrity = loadVisualiserWasmIntegrity();

export default defineConfig(({ command }) => {
    const bundledDev = envBool(process.env.MESHCHAT_VITE_BUNDLED_DEV);

    // Only clear hashed assets on production build. Loading this config for
    // `vite` / `vite preview` must not wipe meshchatx/public/assets used by
    // the Python static server (Lighthouse, packaged UI).
    if (command === "build" && fs.existsSync(assetsDir)) {
        fs.rmSync(assetsDir, { recursive: true, force: true });
    }

    return {
        experimental: bundledDev ? { bundledDev: true } : undefined,
        define: {
            __APP_BUILD_TIME__: JSON.stringify(appBuildTimeIso),
            __VUE_PROD_DEVTOOLS__: "false",
            "import.meta.env.VITE_MICRON_WASM_BUNDLED": JSON.stringify(micronWasmBundled ? "true" : "false"),
            "import.meta.env.VITE_MICRON_PARSER_GO_RELEASE": JSON.stringify(MICRON_PARSER_GO_RELEASE_TAG),
            "import.meta.env.VITE_VISUALISER_WASM_BUNDLED": JSON.stringify(visualiserWasmBundled ? "true" : "false"),
            __MICRON_WASM_SRI_WASM__: JSON.stringify(micronWasmIntegrity?.wasm || ""),
            __MICRON_WASM_SRI_EXEC__: JSON.stringify(micronWasmIntegrity?.wasmExec || ""),
            __VISUALISER_WASM_SRI_WASM__: JSON.stringify(visualiserWasmIntegrity?.wasm || ""),
            __VISUALISER_WASM_SRI_EXEC__: JSON.stringify(visualiserWasmIntegrity?.wasmExec || ""),
        },
        plugins: [
            tailwindcss(),
            ...(isVueDevToolsEnabled({ command })
                ? [
                      vueDevTools({
                          launchEditor: detectLaunchEditor(),
                      }),
                  ]
                : []),
            vue({
                template: {
                    compilerOptions: {
                        isCustomElement: (tag) => tag === "emoji-picker",
                    },
                },
            }),
            meshchatxServiceWorkerPlugin({ buildId: appBuildTimeIso }),
        ],

        css: {
            devSourcemap: true,
        },

        server: {
            host: "127.0.0.1",
            port: 5173,
            strictPort: true,
            clearScreen: false,
            forwardConsole: command === "serve",
            warmup: {
                clientFiles: ["./main.js", "./components/App.vue", "./components/messages/MessagesPage.vue"],
            },
            proxy: {
                "/api": {
                    target: e2eBackendOrigin,
                    changeOrigin: true,
                    configure: configureQuietProxyErrors,
                    ...backendProxyTls,
                },
                // More specific WS path before the /ws prefix match.
                "/ws/telephone/audio": {
                    target: e2eBackendOrigin,
                    ws: true,
                    changeOrigin: true,
                    configure: configureQuietProxyErrors,
                    ...backendProxyTls,
                },
                "/ws": {
                    target: e2eBackendOrigin,
                    ws: true,
                    changeOrigin: true,
                    configure: configureQuietProxyErrors,
                    ...backendProxyTls,
                },
                "/reticulum-docs": {
                    target: e2eBackendOrigin,
                    changeOrigin: true,
                    configure: configureQuietProxyErrors,
                    ...backendProxyTls,
                },
                "/meshchatx-docs": {
                    target: e2eBackendOrigin,
                    changeOrigin: true,
                    configure: configureQuietProxyErrors,
                    ...backendProxyTls,
                },
            },
        },

        // vite app is loaded from /meshchatx/src/frontend
        root: path.join(__dirname, "meshchatx", "src", "frontend"),

        publicDir: path.join(__dirname, "meshchatx", "src", "frontend", "public"),

        build: {
            sourcemap: false,
            chunkImportMap: true,
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
            include: ["vue", "emoji-picker-element"],
        },

        resolve: {
            dedupe: ["vue"],
            tsconfigPaths: true,
        },
    };
});
