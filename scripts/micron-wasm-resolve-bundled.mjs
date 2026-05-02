/**
 * Resolve paths and detect whether micron-parser-go WASM artifacts are present for Vite/Vitest.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Repository root (parent of scripts/). */
export function micronWasmRepoRoot() {
    return path.join(__dirname, "..");
}

export function micronWasmVendorPaths(repoRoot = micronWasmRepoRoot()) {
    const dir = path.join(repoRoot, "meshchatx", "src", "frontend", "public", "vendor", "micron-parser-go");
    return {
        dir,
        wasm: path.join(dir, "micron-parser-go.wasm"),
        wasmExec: path.join(dir, "wasm_exec.js"),
    };
}

/**
 * True when both wasm_exec.js and a minimally-sized WASM binary exist (build-time fetch succeeded).
 */
export function isMicronWasmBundled(repoRoot = micronWasmRepoRoot()) {
    const { wasm, wasmExec } = micronWasmVendorPaths(repoRoot);
    try {
        if (!fs.existsSync(wasm) || !fs.existsSync(wasmExec)) {
            return false;
        }
        const wasmStat = fs.statSync(wasm);
        const execStat = fs.statSync(wasmExec);
        return wasmStat.size >= 8192 && execStat.size >= 1024;
    } catch {
        return false;
    }
}
