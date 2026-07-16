#!/usr/bin/env node
/**
 * Builds visualiser-wasm (Go) and copies artifacts into frontend public vendor/.
 * Writes integrity.json with SHA-384 SRI hashes.
 * Safe offline: if Go is missing, exits 0 when VISUALISER_WASM_SKIP=1.
 */
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { spawnSync } from "child_process";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const GO_MOD_DIR = path.join(REPO_ROOT, "visualiser-wasm");
const OUT_DIR = path.join(REPO_ROOT, "meshchatx", "src", "frontend", "public", "vendor", "visualiser-wasm");
const WASM_NAME = "visualiser.wasm";
const EXEC_NAME = "wasm_exec.js";
const VERSION = "1.2.0";

function computeSri(buf) {
    return `sha384-${crypto.createHash("sha384").update(buf).digest("base64")}`;
}

function findWasmExec() {
    const fromEnv = process.env.VISUALISER_GO_WASM_EXEC;
    if (fromEnv && fs.existsSync(fromEnv)) {
        return fromEnv;
    }
    const goEnv = spawnSync("go", ["env", "GOROOT"], { encoding: "utf8" });
    if (goEnv.status !== 0) {
        return null;
    }
    const root = goEnv.stdout.trim();
    const candidates = [
        path.join(root, "lib", "wasm", "wasm_exec.js"),
        path.join(root, "misc", "wasm", "wasm_exec.js"),
    ];
    for (const c of candidates) {
        if (fs.existsSync(c)) {
            return c;
        }
    }
    return null;
}

function main() {
    if (process.env.VISUALISER_WASM_SKIP === "1") {
        console.log("build-visualiser-wasm: VISUALISER_WASM_SKIP=1, skipping.");
        process.exit(0);
    }

    if (!fs.existsSync(path.join(GO_MOD_DIR, "go.mod"))) {
        console.warn("build-visualiser-wasm: visualiser-wasm/go.mod missing, skipping.");
        process.exit(0);
    }

    const goCheck = spawnSync("go", ["version"], { encoding: "utf8" });
    if (goCheck.status !== 0) {
        if (process.env.MESHCHATX_OFFLINE_BUILD === "1") {
            const wasmPath = path.join(OUT_DIR, WASM_NAME);
            const execPath = path.join(OUT_DIR, EXEC_NAME);
            if (fs.existsSync(wasmPath) && fs.existsSync(execPath)) {
                console.log("build-visualiser-wasm: go missing but artifacts present (offline).");
                process.exit(0);
            }
            console.error("build-visualiser-wasm: MESHCHATX_OFFLINE_BUILD=1 but artifacts missing and go unavailable.");
            process.exit(1);
        }
        console.warn("build-visualiser-wasm: go not found, skipping (JS fallback will be used).");
        process.exit(0);
    }

    fs.mkdirSync(OUT_DIR, { recursive: true });
    const wasmOut = path.join(OUT_DIR, WASM_NAME);
    const build = spawnSync("go", ["build", "-trimpath", "-ldflags=-s -w", "-o", wasmOut, "./cmd/wasm"], {
        cwd: GO_MOD_DIR,
        env: { ...process.env, GOOS: "js", GOARCH: "wasm" },
        encoding: "utf8",
    });
    if (build.status !== 0) {
        console.error(build.stderr || build.stdout || "go build failed");
        process.exit(1);
    }

    const execSrc = findWasmExec();
    if (!execSrc) {
        console.error("build-visualiser-wasm: wasm_exec.js not found under GOROOT");
        process.exit(1);
    }
    const execOut = path.join(OUT_DIR, EXEC_NAME);
    fs.copyFileSync(execSrc, execOut);

    const wasmBuf = fs.readFileSync(wasmOut);
    const execBuf = fs.readFileSync(execOut);
    const integrity = {
        version: VERSION,
        wasm: computeSri(wasmBuf),
        wasmExec: computeSri(execBuf),
        wasmExecSource: execSrc,
    };
    fs.writeFileSync(path.join(OUT_DIR, "integrity.json"), JSON.stringify(integrity, null, 2) + "\n");
    console.log(`build-visualiser-wasm: OK (${wasmBuf.length} bytes WASM, SRI written to vendor/visualiser-wasm/)`);
}

main();
