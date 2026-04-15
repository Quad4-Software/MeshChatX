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

function stripPythonBytecodeArtifacts(dir) {
    if (!fs.existsSync(dir)) return;
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const ent of entries) {
        const full = path.join(dir, ent.name);
        if (ent.isDirectory()) {
            if (ent.name === "__pycache__") {
                fs.rmSync(full, { recursive: true, force: true });
            } else {
                stripPythonBytecodeArtifacts(full);
            }
        } else if (ent.name.endsWith(".pyc") || ent.name.endsWith(".pyo")) {
            fs.unlinkSync(full);
        }
    }
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
    const arch = process.env.ARCH || process.arch;
    const isWin = platform === "win32" || platform === "win";
    const isDarwin = platform === "darwin";
    const targetName = isWin ? "ReticulumMeshChatX.exe" : "ReticulumMeshChatX";

    let platformFolder = "linux";
    if (isWin) {
        platformFolder = "win32";
    } else if (isDarwin) {
        platformFolder = "darwin";
    }
    const buildDirRelative = `build/exe/${platformFolder}-${arch}`;
    const buildDir = path.join(__dirname, "..", buildDirRelative);

    // Allow overriding the python command
    const pythonCmd = process.env.PYTHON_CMD || "poetry run python";

    console.log(
        `Building backend for ${platform} (target: ${targetName}, output: ${buildDirRelative}) using: ${pythonCmd}`
    );

    const env = {
        ...process.env,
        CX_FREEZE_TARGET_NAME: targetName,
        CX_FREEZE_BUILD_EXE: buildDirRelative,
        PYTHONDONTWRITEBYTECODE: "1",
    };

    const cmdParts = pythonCmd.trim().split(/\s+/).filter(Boolean);
    const cmd = cmdParts[0];
    const baseArgs = cmdParts.slice(1);
    const licensesArgs = [...baseArgs, "-m", "meshchatx.src.backend.licenses_collector", "--write-artifacts"];
    const args = [...baseArgs, "cx_setup.py", "build"];

    let spawnCmd = cmd;
    let spawnArgs = licensesArgs;
    const rosettaX64 = isDarwin && arch === "x64" && process.arch === "arm64" && !process.env.PYTHON_CMD;
    if (rosettaX64) {
        spawnCmd = "arch";
        spawnArgs = ["-x86_64", cmd, ...licensesArgs];
    }

    console.log("Generating embedded third-party license artifacts...");
    const licensesResult = spawnSync(spawnCmd, spawnArgs, {
        stdio: "inherit",
        shell: false,
        env: env,
    });
    if (licensesResult.error) {
        throw licensesResult.error;
    }
    if (licensesResult.status !== 0) {
        process.exit(licensesResult.status || 1);
    }

    spawnCmd = cmd;
    spawnArgs = args;
    if (rosettaX64) {
        spawnCmd = "arch";
        spawnArgs = ["-x86_64", cmd, ...args];
    }

    const result = spawnSync(spawnCmd, spawnArgs, {
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
        if (isDarwin) {
            stripPythonBytecodeArtifacts(buildDir);
        }
        const manifestPath = path.join(buildDir, "backend-manifest.json");
        const skipManifest =
            process.env.MESHCHATX_SKIP_BACKEND_MANIFEST === "1" ||
            process.env.MESHCHATX_SKIP_BACKEND_MANIFEST === "true";
        if (skipManifest) {
            if (fs.existsSync(manifestPath)) {
                fs.unlinkSync(manifestPath);
            }
            console.log(
                "Skipping backend-manifest.json (MESHCHATX_SKIP_BACKEND_MANIFEST); universal merge requires identical non-binary files."
            );
        } else {
            generateManifest(buildDir, manifestPath);
        }
    } else {
        console.error(`Build directory not found (${buildDir}), manifest generation skipped.`);
    }
} catch (error) {
    console.error("Build failed:", error.message);
    process.exit(1);
}
