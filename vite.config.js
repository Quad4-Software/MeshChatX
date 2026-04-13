import path from "path";
import fs from "fs";
import { defineConfig } from "vite";
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

export default defineConfig({
    plugins: [vue(), vuetify()],

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
        include: ["dayjs", "vue"],
    },

    resolve: {
        dedupe: ["vue"],
    },
});
