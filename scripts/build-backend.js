#!/usr/bin/env node

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

function getFiles(dir, fileList = []) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const name = path.join(dir, file);
        if (fs.statSync(name).isDirectory()) {
            getFiles(name, fileList);
        } else {
            fileList.push(name);
        }
    }
    return fileList;
}

function generateManifest(buildDir, manifestPath) {
    console.log("Generating backend integrity manifest...");
    const files = getFiles(buildDir);
    const manifest = {};

    for (const file of files) {
        const relativePath = path.relative(buildDir, file);
        const fileBuffer = fs.readFileSync(file);
        const hash = crypto.createHash("sha256").update(fileBuffer).digest("hex");
        manifest[relativePath] = hash;
    }

    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    console.log(`Manifest saved to ${manifestPath} (${Object.keys(manifest).length} files)`);
}

try {
    console.log("Building backend with cx_Freeze...");
    const result = spawnSync("poetry", ["run", "python", "cx_setup.py", "build"], { stdio: "inherit", shell: false });
    if (result.error) {
        throw result.error;
    }
    if (result.status !== 0) {
        process.exit(result.status || 1);
    }

    const buildDir = path.join(__dirname, "..", "build", "exe");
    const manifestPath = path.join(__dirname, "..", "electron", "backend-manifest.json");

    if (fs.existsSync(buildDir)) {
        generateManifest(buildDir, manifestPath);
    } else {
        console.error("Build directory not found, manifest generation skipped.");
    }
} catch (error) {
    console.error("Build failed:", error.message);
    process.exit(1);
}
