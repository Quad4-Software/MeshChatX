// SPDX-License-Identifier: 0BSD
/**
 * Generate MeshChatX service-worker.js from shared PWA modules + bootstrap template.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");

export const SW_TEMPLATE_PATH = path.join(
    REPO_ROOT,
    "meshchatx",
    "src",
    "frontend",
    "sw",
    "service-worker.template.js"
);

export const SW_POLICY_PATH = path.join(
    REPO_ROOT,
    "meshchatx",
    "src",
    "frontend",
    "js",
    "pwa",
    "swCachePolicy.js"
);

export const SW_RUNTIME_PATH = path.join(
    REPO_ROOT,
    "meshchatx",
    "src",
    "frontend",
    "js",
    "pwa",
    "swShellRuntime.js"
);

export const SW_PUBLIC_PATH = path.join(
    REPO_ROOT,
    "meshchatx",
    "src",
    "frontend",
    "public",
    "service-worker.js"
);

export const DEFAULT_SHELL_PRECACHE = [
    "/",
    "/boot-theme.js",
    "/manifest.json",
    "/favicons/favicon-512x512.png",
];

/**
 * Strip ESM import/export so modules can be inlined into a classic service worker.
 * @param {string} source
 * @returns {string}
 */
export function stripEsmForServiceWorker(source) {
    return String(source || "")
        .replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*;?\s*$/gm, "")
        .replace(/^export\s+async\s+function\s+/gm, "async function ")
        .replace(/^export\s+function\s+/gm, "function ")
        .replace(/^export\s+const\s+/gm, "const ")
        .replace(/^export\s+\{[^}]*\}\s*;?\s*$/gm, "")
        .replace(/^\/\/ SPDX-License-Identifier:.*$/gm, "")
        .trim();
}

/**
 * @param {string} assetsDir absolute path to meshchatx/public/assets
 * @returns {string[]}
 */
export function collectAssetPrecacheUrls(assetsDir) {
    const urls = [];
    if (!assetsDir || !fs.existsSync(assetsDir)) {
        return urls;
    }
    const walk = (dir, prefix) => {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const abs = path.join(dir, entry.name);
            const rel = `${prefix}/${entry.name}`.replace(/\\/g, "/");
            if (entry.isDirectory()) {
                walk(abs, rel);
            } else if (entry.isFile()) {
                urls.push(rel);
            }
        }
    };
    walk(assetsDir, "/assets");
    urls.sort();
    return urls;
}

/**
 * @param {{ buildId?: string, precacheUrls?: string[], templatePath?: string }} options
 * @returns {string}
 */
export function renderServiceWorkerSource(options = {}) {
    const templatePath = options.templatePath || SW_TEMPLATE_PATH;
    const buildId = options.buildId || "dev";
    const precacheUrls = Array.isArray(options.precacheUrls)
        ? options.precacheUrls
        : DEFAULT_SHELL_PRECACHE;
    const template = fs.readFileSync(templatePath, "utf8");
    if (!template.includes("__MESHCHATX_SW_BUILD_ID__") || !template.includes("__MESHCHATX_SW_PRECACHE_JSON__")) {
        throw new Error("service-worker template missing injection placeholders");
    }
    const policy = stripEsmForServiceWorker(fs.readFileSync(SW_POLICY_PATH, "utf8"));
    const runtime = stripEsmForServiceWorker(fs.readFileSync(SW_RUNTIME_PATH, "utf8"));
    const bootstrap = template
        .replaceAll("__MESHCHATX_SW_BUILD_ID__", String(buildId))
        .replaceAll("__MESHCHATX_SW_PRECACHE_JSON__", JSON.stringify(precacheUrls));
    return [
        "// SPDX-License-Identifier: 0BSD",
        "/* eslint-disable no-restricted-globals */",
        "/* Generated MeshChatX service worker. Do not edit by hand. */",
        policy,
        runtime,
        bootstrap,
    ].join("\n\n");
}

/**
 * @param {{
 *   buildId?: string,
 *   precacheUrls?: string[],
 *   outfile?: string,
 *   assetsDir?: string,
 * }} options
 * @returns {{ outfile: string, buildId: string, precacheUrls: string[] }}
 */
export function writeServiceWorker(options = {}) {
    const outfile = options.outfile || SW_PUBLIC_PATH;
    const buildId = options.buildId || "dev";
    const fromAssets = options.assetsDir ? collectAssetPrecacheUrls(options.assetsDir) : [];
    const base = Array.isArray(options.precacheUrls) ? options.precacheUrls : DEFAULT_SHELL_PRECACHE;
    const precacheUrls = [...new Set([...base, ...fromAssets])];
    const source = renderServiceWorkerSource({ buildId, precacheUrls });
    fs.mkdirSync(path.dirname(outfile), { recursive: true });
    fs.writeFileSync(outfile, source, "utf8");
    return { outfile, buildId, precacheUrls };
}

/**
 * Vite plugin: write a dev SW into public/ and a production SW into outDir after bundle.
 * @param {{ buildId: string }} options
 */
export function meshchatxServiceWorkerPlugin(options) {
    const buildId = options?.buildId || "dev";
    return {
        name: "meshchatx-service-worker",
        buildStart() {
            writeServiceWorker({
                buildId: "dev",
                precacheUrls: DEFAULT_SHELL_PRECACHE,
                outfile: SW_PUBLIC_PATH,
            });
        },
        closeBundle() {
            const outDir = path.join(REPO_ROOT, "meshchatx", "public");
            const assetsDir = path.join(outDir, "assets");
            writeServiceWorker({
                buildId,
                assetsDir,
                precacheUrls: DEFAULT_SHELL_PRECACHE,
                outfile: path.join(outDir, "service-worker.js"),
            });
            writeServiceWorker({
                buildId: "dev",
                precacheUrls: DEFAULT_SHELL_PRECACHE,
                outfile: SW_PUBLIC_PATH,
            });
        },
    };
}
