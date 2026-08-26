#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const SRC_CSS = path.join(REPO_ROOT, "electron", "assets", "css", "electron-shell.src.css");
const ELECTRON_OUT = path.join(REPO_ROOT, "electron", "assets", "css", "electron-shell.css");
const PUBLIC_OUT = path.join(
    REPO_ROOT,
    "meshchatx",
    "src",
    "frontend",
    "public",
    "assets",
    "css",
    "electron-shell.css"
);

function ensureParentDir(filePath) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function buildCss() {
    const result = spawnSync("pnpm", ["exec", "tailwindcss", "-i", SRC_CSS, "-o", ELECTRON_OUT, "--minify"], {
        cwd: REPO_ROOT,
        stdio: "inherit",
    });
    if (result.status !== 0) {
        process.exit(result.status ?? 1);
    }
}

function copyToPublic() {
    ensureParentDir(PUBLIC_OUT);
    fs.copyFileSync(ELECTRON_OUT, PUBLIC_OUT);
}

if (!fs.existsSync(SRC_CSS)) {
    console.error(`build-electron-shell-css: missing source ${SRC_CSS}`);
    process.exit(1);
}

buildCss();
copyToPublic();
console.log(`Wrote ${ELECTRON_OUT}`);
console.log(`Copied to ${PUBLIC_OUT}`);
