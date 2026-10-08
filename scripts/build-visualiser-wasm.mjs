#!/usr/bin/env node
/**
 * Builds visualiser-wasm with TinyGo and copies artifacts into frontend public vendor/.
 * Writes integrity.json with SHA-384 SRI hashes.
 * Safe offline: if Go is missing, exits 0 when VISUALISER_WASM_SKIP=1.
 */
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { spawnSync } from "child_process";
import { fileURLToPath } from "url";
import { assertWasmExecCompat } from "./wasm-exec-compat.mjs";

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

function findTinyGo() {
    const fromEnv = process.env.TINYGO;
    if (fromEnv && fs.existsSync(fromEnv)) {
        return fromEnv;
    }
    const check = spawnSync("tinygo", ["version"], { encoding: "utf8" });
    if (check.status === 0) {
        return "tinygo";
    }
    return null;
}

function findWasmExec() {
    const fromEnv = process.env.VISUALISER_GO_WASM_EXEC;
    if (fromEnv && fs.existsSync(fromEnv)) {
        return fromEnv;
    }
    const tinygo = findTinyGo();
    if (tinygo) {
        const tgEnv = spawnSync(tinygo, ["env", "TINYGOROOT"], { encoding: "utf8" });
        if (tgEnv.status === 0) {
            const cand = path.join(tgEnv.stdout.trim(), "targets", "wasm_exec.js");
            if (fs.existsSync(cand)) {
                return cand;
            }
        }
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

    const requireWasm =
        process.env.MESHCHATX_REQUIRE_VISUALISER_WASM === "1" ||
        process.env.MESHCHATX_REQUIRE_VISUALISER_WASM === "true";

    if (!fs.existsSync(path.join(GO_MOD_DIR, "go.mod"))) {
        const msg = "build-visualiser-wasm: visualiser-wasm/go.mod missing, skipping.";
        if (requireWasm) {
            console.error(msg);
            process.exit(1);
        }
        console.warn(msg);
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
        const msg = "build-visualiser-wasm: go not found, skipping (JS fallback will be used).";
        if (requireWasm) {
            console.error(msg);
            process.exit(1);
        }
        console.warn(msg);
        process.exit(0);
    }

    fs.mkdirSync(OUT_DIR, { recursive: true });
    const wasmOut = path.join(OUT_DIR, WASM_NAME);
    const tinygo = findTinyGo();
    if (!tinygo) {
        const msg =
            "build-visualiser-wasm: tinygo not found. Install TinyGo (see scripts/ci/setup-tinygo.sh) or set TINYGO to the binary path. Stock Go wasm is not used.";
        if (process.env.MESHCHATX_OFFLINE_BUILD === "1") {
            const wasmPath = path.join(OUT_DIR, WASM_NAME);
            const execPath = path.join(OUT_DIR, EXEC_NAME);
            if (fs.existsSync(wasmPath) && fs.existsSync(execPath)) {
                console.log("build-visualiser-wasm: tinygo missing but artifacts present (offline).");
                process.exit(0);
            }
        }
        console.error(msg);
        process.exit(1);
    }
    const build = spawnSync(tinygo, ["build", "-target", "wasm", "-opt=z", "-no-debug", "-o", wasmOut, "./cmd/wasm"], {
        cwd: GO_MOD_DIR,
        env: process.env,
        encoding: "utf8",
    });
    if (build.status !== 0) {
        console.error(build.stderr || build.stdout || "wasm build failed");
        process.exit(1);
    }
    console.log("build-visualiser-wasm: built with TinyGo");

    const execSrc = findWasmExec();
    if (!execSrc) {
        console.error("build-visualiser-wasm: wasm_exec.js not found under GOROOT");
        process.exit(1);
    }
    const execOut = path.join(OUT_DIR, EXEC_NAME);
    fs.rmSync(execOut, { force: true });
    fs.copyFileSync(execSrc, execOut);
    fs.chmodSync(execOut, 0o644);
    assertWasmExecCompat(wasmOut, execOut, "build-visualiser-wasm");

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
