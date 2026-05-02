#!/usr/bin/env node
/**
 * Downloads micron-parser-go WASM release assets and matching wasm_exec.js for Vite public/.
 * Generates SRI hashes for integrity verification at runtime.
 * Safe to run offline: exits 0 without files when MICRON_WASM_SKIP=1 or network fails.
 *
 * Override URLs:
 *   MICRON_PARSER_GO_WASM_URL
 *   MICRON_GO_WASM_EXEC_URL
 */
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { MICRON_PARSER_GO_RELEASE_TAG } from "./micron-parser-go-version.mjs";
import { micronWasmVendorPaths, micronWasmRepoRoot } from "./micron-wasm-resolve-bundled.mjs";

const DEFAULT_WASM_URL = `https://github.com/Quad4-Software/Micron-Parser-Go/releases/download/${MICRON_PARSER_GO_RELEASE_TAG}/micron-parser-go.wasm`;
const DEFAULT_WASM_EXEC_URL = "https://raw.githubusercontent.com/golang/go/go1.26.2/lib/wasm/wasm_exec.js";

const TIMEOUT_MS = Number(process.env.MICRON_WASM_FETCH_TIMEOUT_MS || 120000);

function rmQuiet(p) {
    try {
        fs.rmSync(p, { force: true });
    } catch {
        /* ignore */
    }
}

function computeSriHash(buf) {
    const hash = crypto.createHash("sha384").update(buf).digest("base64");
    return `sha384-${hash}`;
}

async function fetchBinary(url, destFile) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    try {
        const res = await fetch(url, { signal: ctrl.signal });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const buf = Buffer.from(await res.arrayBuffer());
        fs.mkdirSync(path.dirname(destFile), { recursive: true });
        fs.writeFileSync(destFile, buf);
        return { size: buf.length, sri: computeSriHash(buf) };
    } finally {
        clearTimeout(t);
    }
}

async function main() {
    if (process.env.MICRON_WASM_SKIP === "1") {
        console.log("fetch-micron-wasm: MICRON_WASM_SKIP=1, skipping.");
        process.exit(0);
    }

    const root = micronWasmRepoRoot();
    const { dir, wasm, wasmExec } = micronWasmVendorPaths(root);
    const wasmUrl = process.env.MICRON_PARSER_GO_WASM_URL || DEFAULT_WASM_URL;
    const execUrl = process.env.MICRON_GO_WASM_EXEC_URL || DEFAULT_WASM_EXEC_URL;

    fs.mkdirSync(dir, { recursive: true });

    let wasmResult;
    let execResult;
    try {
        console.log("fetch-micron-wasm: downloading wasm_exec.js...");
        execResult = await fetchBinary(execUrl, wasmExec);
        console.log("fetch-micron-wasm: downloading micron-parser-go.wasm...");
        wasmResult = await fetchBinary(wasmUrl, wasm);
        console.log(`fetch-micron-wasm: OK (${wasmResult.size} bytes WASM)`);
    } catch (e) {
        console.warn("fetch-micron-wasm: failed:", e?.message || e);
        rmQuiet(wasm);
        rmQuiet(wasmExec);
        rmQuiet(path.join(dir, "integrity.json"));
        process.exit(0);
    }

    // Write SRI hashes for runtime verification
    const integrity = {
        version: MICRON_PARSER_GO_RELEASE_TAG,
        wasm: wasmResult.sri,
        wasmExec: execResult.sri,
    };
    fs.writeFileSync(path.join(dir, "integrity.json"), JSON.stringify(integrity, null, 2));
    console.log("fetch-micron-wasm: SRI hashes written to integrity.json");
}

main();
