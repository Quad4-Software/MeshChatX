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

const flatpakForgeTarget =
    args.includes("@electron-forge/maker-flatpak") ||
    process.env.FORGE_MAKE_FLATPAK === "1" ||
    process.env.FORGE_MAKE_FLATPAK === "true";
if (flatpakForgeTarget) {
    const ensure = path.join(root, "scripts", "ensure-flatpak-flathub-remote.sh");
    const pre = spawnSync("bash", [ensure], { cwd: root, stdio: "inherit" });
    if (pre.status !== 0 && pre.status !== null) {
        process.exit(pre.status);
    }
    if (pre.signal) {
        process.exit(1);
    }
}

const result = spawnSync(process.execPath, [forgeCli, ...args], {
    cwd: root,
    env,
    stdio: "inherit",
});

if (result.signal) {
    process.exit(1);
}
process.exit(result.status ?? 1);
