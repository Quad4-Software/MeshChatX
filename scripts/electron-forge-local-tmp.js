#!/usr/bin/env node

// Staging must live outside the repo: packager copies the project into TMPDIR, which cannot be under the source tree.

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const defaultTmpDir = path.join(path.dirname(root), `.forge-tmp-${path.basename(root)}`);
const tmpDir = path.resolve(process.env.FORGE_TMPDIR || defaultTmpDir);
fs.mkdirSync(tmpDir, { recursive: true });

const env = {
    ...process.env,
    TMPDIR: tmpDir,
    TEMP: tmpDir,
    TMP: tmpDir,
};

const forgeCli = require.resolve("@electron-forge/cli/dist/electron-forge.js");
const args = process.argv.slice(2);
const result = spawnSync(process.execPath, [forgeCli, ...args], {
    cwd: root,
    env,
    stdio: "inherit",
});

if (result.signal) {
    process.exit(1);
}
process.exit(result.status ?? 1);
