import path from "path";
import fs from "fs";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vuetify from "vite-plugin-vuetify";

const vendorChunkGroups = [
    { test: /[/\\]node_modules[/\\]vuetify/, name: "vendor-vuetify" },
    { test: /[/\\]node_modules[/\\](vis-network|vis-data)/, name: "vendor-vis" },
    { test: /[/\\]node_modules[/\\]vue-router/, name: "vendor-vue-router" },
    { test: /[/\\]node_modules[/\\](protobufjs|@protobufjs)/, name: "vendor-protobuf" },
    { test: /[/\\]node_modules[/\\]dayjs/, name: "vendor-dayjs" },
    { test: /[/\\]node_modules[/\\]@mdi(?:\/|\\)js/, name: "vendor-mdi" },
    { test: /[/\\]node_modules[/\\]compressorjs/, name: "vendor-compressor" },
    { test: /[/\\]node_modules[/\\]click-outside-vue3/, name: "vendor-click-outside" },
    { test: /[/\\]node_modules[/\\]mitt/, name: "vendor-mitt" },
    { test: /[/\\]node_modules[/\\]micron-parser/, name: "vendor-micron" },
    { test: /MicronParser\.js/, name: "vendor-micron" },
    { test: /[/\\]node_modules[/\\]electron-prompt/, name: "vendor-electron-prompt" },
    { test: /[/\\]node_modules[/\\].*vue/, name: "vendor-vue" },
    { test: /[/\\]node_modules[/\\]/, name: "vendor-other" },
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
                    groups: vendorChunkGroups,
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
