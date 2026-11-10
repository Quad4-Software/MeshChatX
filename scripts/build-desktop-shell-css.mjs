#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD

// Builds the embedded desktop shell stylesheet (desktop/shell) and mirrors it
// into the frontend public assets for the standalone RNode flasher page.

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const SRC_CSS = path.join(REPO_ROOT, "desktop", "shell", "assets", "css", "desktop-shell.src.css");
const SHELL_OUT = path.join(REPO_ROOT, "desktop", "shell", "assets", "css", "desktop-shell.css");
const PUBLIC_OUT = path.join(REPO_ROOT, "meshchatx", "src", "frontend", "public", "assets", "css", "desktop-shell.css");

function ensureParentDir(filePath) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function buildCss() {
    // Invoke the installed bin directly: `pnpm exec` is not spawnable in
    // every container image (Chainguard/Wolfi node) and dies silently.
    const tailwindBin = path.join(
        REPO_ROOT,
        "node_modules",
        ".bin",
        process.platform === "win32" ? "tailwindcss.cmd" : "tailwindcss"
    );
    const result = spawnSync(tailwindBin, ["-i", SRC_CSS, "-o", SHELL_OUT, "--minify"], {
        cwd: REPO_ROOT,
        stdio: "inherit",
    });
    if (result.status !== 0) {
        process.exit(result.status ?? 1);
    }
}

function copyToPublic() {
    ensureParentDir(PUBLIC_OUT);
    fs.copyFileSync(SHELL_OUT, PUBLIC_OUT);
}

buildCss();
copyToPublic();
console.log("desktop shell css built ->", SHELL_OUT);
