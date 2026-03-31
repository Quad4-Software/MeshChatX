import path from "path";
import fs from "fs";
import vue from "@vitejs/plugin-vue";
import vuetify from "vite-plugin-vuetify";

// Purge old assets before build to prevent accumulation
const assetsDir = path.join(__dirname, "meshchatx", "public", "assets");
if (fs.existsSync(assetsDir)) {
    fs.rmSync(assetsDir, { recursive: true, force: true });
}

const e2eBackendPort = process.env.E2E_BACKEND_PORT || "8000";
const e2eBackendOrigin = `http://127.0.0.1:${e2eBackendPort}`;
const e2eBackendWs = `ws://127.0.0.1:${e2eBackendPort}`;

export default {
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

        rollupOptions: {
            treeshake: {
                moduleSideEffects: (id) => {
                    if (id.includes("@mdi/js")) {
                        return false;
                    }
                    return null;
                },
            },
            input: {
                // we want to use /meshchatx/src/frontend/index.html as the entrypoint for this vite app
                app: path.join(__dirname, "meshchatx", "src", "frontend", "index.html"),
            },
            output: {
                manualChunks(id) {
                    if (id.includes("node_modules")) {
                        if (id.includes("vuetify")) {
                            return "vendor-vuetify";
                        }
                        if (id.includes("vis-network") || id.includes("vis-data")) {
                            return "vendor-vis";
                        }
                        if (id.includes("vue-router")) {
                            return "vendor-vue-router";
                        }
                        if (id.includes("vue")) {
                            return "vendor-vue";
                        }
                        if (id.includes("protobufjs") || id.includes("@protobufjs")) {
                            return "vendor-protobuf";
                        }
                        if (id.includes("dayjs")) {
                            return "vendor-dayjs";
                        }
                        if (id.includes("axios")) {
                            return "vendor-axios";
                        }
                        if (id.includes("@mdi/js")) {
                            return "vendor-mdi";
                        }
                        if (id.includes("compressorjs")) {
                            return "vendor-compressor";
                        }
                        if (id.includes("click-outside-vue3")) {
                            return "vendor-click-outside";
                        }
                        if (id.includes("mitt")) {
                            return "vendor-mitt";
                        }
                        if (id.includes("micron-parser") || id.includes("MicronParser.js")) {
                            return "vendor-micron";
                        }
                        if (id.includes("electron-prompt")) {
                            return "vendor-electron-prompt";
                        }
                        return "vendor-other";
                    }
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
};
