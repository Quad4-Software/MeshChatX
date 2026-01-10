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
    const manifest = {
        _metadata: {
            version: 1,
            date: new Date().toISOString().split("T")[0],
            time: new Date().toISOString().split("T")[1].split(".")[0],
        },
        files: {},
    };

    for (const file of files) {
        const relativePath = path.relative(buildDir, file);
        if (relativePath === "backend-manifest.json") continue;
        const fileBuffer = fs.readFileSync(file);
        const hash = crypto.createHash("sha256").update(fileBuffer).digest("hex");
        manifest.files[relativePath] = hash;
    }

    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    console.log(`Manifest saved to ${manifestPath} (${Object.keys(manifest.files).length} files)`);
}

try {
    const platform = process.env.PLATFORM || process.platform;
    const isWin = platform === "win32" || platform === "win";
    const targetName = isWin ? "ReticulumMeshChatX.exe" : "ReticulumMeshChatX";
    const buildDirRelative = isWin ? "build/exe/win32" : "build/exe/linux";
    const buildDir = path.join(__dirname, "..", buildDirRelative);

    console.log(
        `Building backend for ${platform} (target: ${targetName}, output: ${buildDirRelative}) with cx_Freeze...`
    );

    const env = {
        ...process.env,
        CX_FREEZE_TARGET_NAME: targetName,
        CX_FREEZE_BUILD_EXE: buildDirRelative,
    };
    const result = spawnSync("poetry", ["run", "python", "cx_setup.py", "build"], {
        stdio: "inherit",
        shell: false,
        env: env,
    });
    if (result.error) {
        throw result.error;
    }
    if (result.status !== 0) {
        process.exit(result.status || 1);
    }

    if (fs.existsSync(buildDir)) {
        const manifestPath = path.join(buildDir, "backend-manifest.json");
        generateManifest(buildDir, manifestPath);
    } else {
        console.error(`Build directory not found (${buildDir}), manifest generation skipped.`);
    }
} catch (error) {
    console.error("Build failed:", error.message);
    process.exit(1);
}
