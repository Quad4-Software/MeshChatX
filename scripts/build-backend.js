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

function stripDuplicateMeshchatxPublic(buildDir) {
    const dup = path.join(buildDir, "lib", "meshchatx", "public");
    if (!fs.existsSync(dup)) {
        return;
    }
    console.log("Removing lib/meshchatx/public from cx_Freeze output.");
    fs.rmSync(dup, { recursive: true, force: true });
}

function stripMeshchatxFrontendSources(buildDir) {
    const fe = path.join(buildDir, "lib", "meshchatx", "src", "frontend");
    if (!fs.existsSync(fe)) {
        return;
    }
    const keepRel = path.join("public", "repository-server-index.html");
    const keepPath = path.join(fe, keepRel);
    let buf = null;
    if (fs.existsSync(keepPath)) {
        buf = fs.readFileSync(keepPath);
    }
    console.log(
        "Trimming meshchatx/src/frontend to repository-server-index.html only (Vue sources are unused at runtime)."
    );
    fs.rmSync(fe, { recursive: true, force: true });
    if (buf) {
        const dest = path.join(fe, keepRel);
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.writeFileSync(dest, buf);
    }
}

function stripFrozenPythonBloat(buildDir) {
    const lib = path.join(buildDir, "lib");
    if (!fs.existsSync(lib)) {
        return;
    }
    for (const name of ["pydoc_data", "setuptools"]) {
        const p = path.join(lib, name);
        if (fs.existsSync(p)) {
            console.log(`Removing lib/${name} from cx_Freeze output.`);
            fs.rmSync(p, { recursive: true, force: true });
        }
    }
    const numpyRoot = path.join(lib, "numpy");
    if (!fs.existsSync(numpyRoot)) {
        return;
    }
    const stack = [numpyRoot];
    while (stack.length) {
        const dir = stack.pop();
        let entries;
        try {
            entries = fs.readdirSync(dir, { withFileTypes: true });
        } catch {
            continue;
        }
        for (const ent of entries) {
            if (!ent.isDirectory()) {
                continue;
            }
            const full = path.join(dir, ent.name);
            if (ent.name === "tests") {
                console.log(`Removing ${path.relative(buildDir, full)} from cx_Freeze output.`);
                fs.rmSync(full, { recursive: true, force: true });
            } else {
                stack.push(full);
            }
        }
    }
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
            const stem = ent.name.replace(/\.pyc$/i, "").replace(/\.pyo$/i, "");
            const siblingPy = path.join(dir, `${stem}.py`);
            if (fs.existsSync(siblingPy)) {
                fs.unlinkSync(full);
            }
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

function failOnSpawnResult(stepName, result) {
    if (result.error) {
        throw result.error;
    }

    if (result.signal) {
        console.error(`${stepName} was terminated by signal ${result.signal}.`);
        if (result.signal === "SIGKILL") {
            console.error(
                "Build process was force-killed (often OOM killer). This is likely memory pressure, not a normal script error."
            );
        }
        process.exit(1);
    }

    if (result.status !== 0) {
        console.error(`${stepName} exited with status ${result.status}.`);
        process.exit(result.status || 1);
    }
}

function fileMtimeMs(filePath) {
    if (!fs.existsSync(filePath)) {
        return null;
    }
    return fs.statSync(filePath).mtimeMs;
}

function shouldRefreshLicenseArtifacts(repoRoot) {
    const forceRefresh =
        process.env.MESHCHATX_FORCE_LICENSE_ARTIFACTS === "1" ||
        process.env.MESHCHATX_FORCE_LICENSE_ARTIFACTS === "true";
    if (forceRefresh) {
        return true;
    }

    const dataDir = path.join(repoRoot, "meshchatx", "src", "backend", "data");
    const noticesPath = path.join(dataDir, "THIRD_PARTY_NOTICES.txt");
    const frontendLicensesPath = path.join(dataDir, "licenses_frontend.json");

    const outputTimes = [fileMtimeMs(noticesPath), fileMtimeMs(frontendLicensesPath)];
    if (outputTimes.some((t) => t == null)) {
        return true;
    }
    const oldestOutput = Math.min(...outputTimes);

    const inputFiles = [
        path.join(repoRoot, "pyproject.toml"),
        path.join(repoRoot, "uv.lock"),
        path.join(repoRoot, "package.json"),
        path.join(repoRoot, "pnpm-lock.yaml"),
        path.join(repoRoot, "meshchatx", "src", "backend", "licenses_collector.py"),
    ];

    let newestInput = 0;
    for (const inputFile of inputFiles) {
        const mtime = fileMtimeMs(inputFile);
        if (mtime != null && mtime > newestInput) {
            newestInput = mtime;
        }
    }

    return newestInput >= oldestOutput;
}

function verifyBinaryArchitecture(buildDir, expectedArch, targetName) {
    const binaryPath = path.join(buildDir, targetName);
    if (!fs.existsSync(binaryPath)) {
        console.warn(`Binary not found at ${binaryPath}, skipping architecture verification.`);
        return true;
    }

    let output = "";
    try {
        const result = spawnSync("file", ["--brief", "--no-pad", binaryPath], {
            encoding: "utf-8",
            shell: false,
        });
        if (result.error || result.status !== 0) {
            console.warn(`Could not verify binary architecture: ${result.error?.message || `exit ${result.status}`}`);
            return true;
        }
        output = result.stdout.toLowerCase();
    } catch (e) {
        console.warn(`Architecture verification failed: ${e.message}`);
        return true;
    }

    const isArm64 = output.includes("aarch64") || output.includes("arm64");
    const isX64 = output.includes("x86-64") || output.includes("x86_64") || output.includes("amd64");

    if (expectedArch === "arm64" && !isArm64) {
        console.error(`Architecture mismatch: expected arm64 but binary is not arm64 (${output.trim()}).`);
        return false;
    }
    if (expectedArch === "x64" && !isX64) {
        console.error(`Architecture mismatch: expected x64 but binary is not x64 (${output.trim()}).`);
        return false;
    }
    return true;
}

try {
    const platform = process.env.PLATFORM || process.platform;
    const arch = process.env.ARCH || process.arch;
    const isWin = platform === "win32" || platform === "win";
    const isDarwin = platform === "darwin";
    const targetName = isWin ? "ReticulumMeshChatX.exe" : "ReticulumMeshChatX";
    const rosettaX64 = isDarwin && arch === "x64" && process.arch === "arm64";

    let platformFolder = "linux";
    if (isWin) {
        platformFolder = "win32";
    } else if (isDarwin) {
        platformFolder = "darwin";
    }
    const buildDirRelative = `build/exe/${platformFolder}-${arch}`;
    const buildDir = path.join(__dirname, "..", buildDirRelative);

    if (arch !== process.arch && !rosettaX64 && !process.env.PYTHON_CMD) {
        console.error(
            `Cross-compilation detected (host: ${process.arch}, target: ${arch}).\n` +
                `cx_Freeze produces binaries for the architecture of the Python interpreter it runs under.\n` +
                `To build the backend for ${arch}, you must either:\n` +
                `  - Build natively on ${arch} hardware (or in a VM/container of that architecture).\n` +
                `  - Set PYTHON_CMD to a ${arch} Python interpreter (with Poetry dependencies installed).\n` +
                `  - Use Docker with QEMU/binfmt support (e.g., docker run --platform ${platformFolder}/${arch}).`
        );
        process.exit(1);
    }

    // Allow overriding the python command
    const pythonCmd = process.env.PYTHON_CMD || "uv run python";

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
    if (rosettaX64) {
        spawnCmd = "arch";
        spawnArgs = ["-x86_64", cmd, ...licensesArgs];
    }

    const repoRoot = path.join(__dirname, "..");
    if (shouldRefreshLicenseArtifacts(repoRoot)) {
        console.log("Generating embedded third-party license artifacts...");
        const licensesResult = spawnSync(spawnCmd, spawnArgs, {
            stdio: "inherit",
            shell: false,
            env: env,
        });
        failOnSpawnResult("License artifact generation", licensesResult);
    } else {
        console.log("Skipping license artifact generation (artifacts are up to date).");
    }

    spawnCmd = cmd;
    spawnArgs = args;
    if (rosettaX64) {
        spawnCmd = "arch";
        spawnArgs = ["-x86_64", cmd, ...args];
    }

    console.log("Running cx_Freeze backend build...");
    const result = spawnSync(spawnCmd, spawnArgs, {
        stdio: "inherit",
        shell: false,
        env: env,
    });
    failOnSpawnResult("Backend build", result);

    if (fs.existsSync(buildDir)) {
        stripDuplicateMeshchatxPublic(buildDir);
        stripMeshchatxFrontendSources(buildDir);
        stripFrozenPythonBloat(buildDir);
        if (isDarwin) {
            stripPythonBytecodeArtifacts(buildDir);
        }
        if (!verifyBinaryArchitecture(buildDir, arch, targetName)) {
            process.exit(1);
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
