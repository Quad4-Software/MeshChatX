#!/usr/bin/env node
/**
 * Copies Bergamot WASM worker files from the npm package to public/vendor/bergamot/.
 *
 * Safe to run offline: exits 0 if the package is missing and artifacts already
 * exist. MESHCHATX_OFFLINE_BUILD=1 only checks that artifacts are present.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, "..");
const vendorDir = path.join(repoRoot, "meshchatx", "src", "frontend", "public", "vendor", "bergamot");
const packageDir = path.join(repoRoot, "node_modules", "@browsermt", "bergamot-translator", "worker");

const files = ["bergamot-translator-worker.js", "bergamot-translator-worker.wasm", "translator-worker.js"];

function main() {
    if (process.env.MESHCHATX_OFFLINE_BUILD === "1") {
        for (const file of files) {
            const dest = path.join(vendorDir, file);
            if (!fs.existsSync(dest)) {
                console.error(`copy-bergamot-wasm: MESHCHATX_OFFLINE_BUILD=1 but ${dest} is missing.`);
                process.exit(1);
            }
        }
        console.log("copy-bergamot-wasm: offline build and artifacts present.");
        return;
    }

    if (!fs.existsSync(packageDir)) {
        console.warn(`copy-bergamot-wasm: package directory ${packageDir} not found.`);
        if (files.every((file) => fs.existsSync(path.join(vendorDir, file)))) {
            console.log("copy-bergamot-wasm: existing vendor artifacts found, skipping.");
            return;
        }
        console.error("copy-bergamot-wasm: no vendor artifacts and no package.");
        process.exit(1);
    }

    fs.mkdirSync(vendorDir, { recursive: true });
    for (const file of files) {
        const src = path.join(packageDir, file);
        const dest = path.join(vendorDir, file);
        if (!fs.existsSync(src)) {
            console.error(`copy-bergamot-wasm: missing source file ${src}`);
            process.exit(1);
        }
        fs.copyFileSync(src, dest);
    }
    console.log("copy-bergamot-wasm: copied worker files to", vendorDir);
}

main();
