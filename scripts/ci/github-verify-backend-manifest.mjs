#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD
//
// Verify a packaged Electron app tree against backend-manifest.json.
//
// electron-builder's extraResources can silently drop files that the build
// manifest hashed (for example dotfile keep-markers under data/). A missing
// entry then surfaces at runtime as a backend integrity "Missing:" warning
// that blocks onboarding. This script replays verifyBackendIntegrity() from
// electron/backendIntegrity.js against the unpacked staging tree so CI fails
// on the drop instead of users.
//
// usage: node scripts/ci/github-verify-backend-manifest.mjs <dir>
//   <dir> may be an unpacked app dir (dist/win-unpacked), an .app bundle, or
//   the backend dir itself. The manifest is located by walking the tree.

import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

const MAX_DEPTH = 8;

function* walk(dir, depth = 0) {
    if (depth > MAX_DEPTH) return;
    let entries;
    try {
        entries = readdirSync(dir);
    } catch {
        return;
    }
    for (const name of entries) {
        const full = path.join(dir, name);
        let st;
        try {
            st = statSync(full);
        } catch {
            continue;
        }
        if (st.isDirectory()) {
            yield* walk(full, depth + 1);
        } else {
            yield full;
        }
    }
}

function findManifest(root) {
    for (const file of walk(root)) {
        if (path.basename(file) === "backend-manifest.json") {
            return file;
        }
    }
    return null;
}

function sha256(file) {
    return createHash("sha256").update(readFileSync(file)).digest("hex");
}

function main() {
    const root = process.argv[2];
    if (!root || !existsSync(root)) {
        console.error(`usage: github-verify-backend-manifest.mjs <dir> (missing: ${root})`);
        process.exit(2);
    }

    const manifestPath = findManifest(path.resolve(root));
    if (!manifestPath) {
        console.error(`backend-manifest.json not found under ${root}`);
        process.exit(1);
    }

    const exeDir = path.dirname(manifestPath);
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
    const files = manifest.files || manifest;
    const issues = [];

    for (const [relPath, expectedHash] of Object.entries(files)) {
        const fullPath = path.join(exeDir, relPath);
        if (!existsSync(fullPath)) {
            issues.push(`Missing: ${relPath}`);
            continue;
        }
        if (sha256(fullPath) !== expectedHash) {
            issues.push(`Modified: ${relPath}`);
        }
    }

    if (issues.length > 0) {
        console.error(`Backend integrity check failed under ${exeDir}:`);
        for (const issue of issues) {
            console.error(`  ${issue}`);
        }
        process.exit(1);
    }

    console.log(`Backend manifest verified: ${Object.keys(files).length} files under ${exeDir}`);
}

main();
