#!/usr/bin/env node
/**
 * Downloads micron-parser-go WASM release assets and matching wasm_exec.js for Vite public/.
 * Generates SRI hashes for integrity verification at runtime.
 * Skips large downloads when upstream hashes match local files (SHASUMS256.txt + conditional GET).
 * Safe to run offline: exits 0 without deleting vendor files when MICRON_WASM_SKIP=1 or network fails.
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

const WASM_FILENAME = "micron-parser-go.wasm";
const SHASUMS256_FILENAME = "SHASUMS256.txt";

/** Same line parsing as MicronWasmRuntimeOverride.parseShasums256ForFilename (GNU/BSD shasum). */
function parseShasums256ForFilename(text, filename) {
    if (text == null || filename == null) {
        return null;
    }
    const lines = String(text).split(/\r?\n/);
    for (const raw of lines) {
        const line = raw.trim();
        if (!line || line.startsWith("#")) {
            continue;
        }
        const m = line.match(/^([a-fA-F0-9]{64})\s+\*?(\S+)\s*$/);
        if (!m) {
            continue;
        }
        const name = m[2].trim();
        if (name === filename || name.endsWith(`/${filename}`)) {
            return m[1].toLowerCase();
        }
    }
    return null;
}

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

function sha256HexOfFile(filePath) {
    const buf = fs.readFileSync(filePath);
    return crypto.createHash("sha256").update(buf).digest("hex");
}

function shasumsUrlFromWasmUrl(wasmUrl) {
    const u = new URL(wasmUrl);
    const dirPath = u.pathname.replace(/[^/]+$/, "");
    u.pathname = `${dirPath}${SHASUMS256_FILENAME}`;
    return u.href;
}

async function fetchWithTimeout(url, options = {}) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    try {
        return await fetch(url, { ...options, signal: ctrl.signal });
    } finally {
        clearTimeout(t);
    }
}

async function fetchBinary(url, destFile) {
    const res = await fetchWithTimeout(url);
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    const buf = Buffer.from(await res.arrayBuffer());
    fs.mkdirSync(path.dirname(destFile), { recursive: true });
    fs.writeFileSync(destFile, buf);
    const etag = res.headers.get("etag") || undefined;
    return { size: buf.length, sri: computeSriHash(buf), etag };
}

/**
 * Uses If-None-Match when we have a prior ETag to avoid re-downloading wasm_exec.js if unchanged.
 */
async function fetchWasmExecResolved(execUrl, wasmExecPath, prev) {
    const sameUrl = prev?.wasmExecSourceUrl === execUrl;
    const inm = sameUrl && prev?.wasmExecEtag ? prev.wasmExecEtag : undefined;
    if (inm && fs.existsSync(wasmExecPath)) {
        const res = await fetchWithTimeout(execUrl, {
            headers: { "If-None-Match": inm },
        });
        if (res.status === 304) {
            const buf = fs.readFileSync(wasmExecPath);
            return {
                size: buf.length,
                sri: computeSriHash(buf),
                etag: inm,
                downloaded: false,
            };
        }
        if (res.ok) {
            const buf = Buffer.from(await res.arrayBuffer());
            fs.mkdirSync(path.dirname(wasmExecPath), { recursive: true });
            fs.writeFileSync(wasmExecPath, buf);
            const etag = res.headers.get("etag") || undefined;
            return {
                size: buf.length,
                sri: computeSriHash(buf),
                etag,
                downloaded: true,
            };
        }
        throw new Error(`HTTP ${res.status}`);
    }
    const got = await fetchBinary(execUrl, wasmExecPath);
    return { ...got, downloaded: true };
}

function readIntegrityJson(integrityPath) {
    try {
        const raw = fs.readFileSync(integrityPath, "utf8");
        return JSON.parse(raw);
    } catch {
        return null;
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
    const integrityPath = path.join(dir, "integrity.json");
    const prev = readIntegrityJson(integrityPath);

    fs.mkdirSync(dir, { recursive: true });

    let passedShasumsFetch = false;
    try {
        const shasumsUrl = shasumsUrlFromWasmUrl(wasmUrl);
        const sumsRes = await fetchWithTimeout(shasumsUrl);
        if (!sumsRes.ok) {
            throw new Error(`SHASUMS256 HTTP ${sumsRes.status}`);
        }
        passedShasumsFetch = true;
        const sumsText = await sumsRes.text();
        const upstreamWasmSha256 = parseShasums256ForFilename(sumsText, WASM_FILENAME);
        if (!upstreamWasmSha256) {
            throw new Error(`${WASM_FILENAME} not listed in ${SHASUMS256_FILENAME}`);
        }

        const wasmHashMatches = fs.existsSync(wasm) && sha256HexOfFile(wasm).toLowerCase() === upstreamWasmSha256;
        let wasmResult;
        let wasmDownloaded = false;
        if (wasmHashMatches) {
            console.log(
                `fetch-micron-wasm: ${WASM_FILENAME} unchanged (SHA-256 matches upstream ${SHASUMS256_FILENAME}), skipping download.`
            );
            const buf = fs.readFileSync(wasm);
            wasmResult = { size: buf.length, sri: computeSriHash(buf) };
        } else {
            console.log(`fetch-micron-wasm: downloading ${WASM_FILENAME}...`);
            wasmResult = await fetchBinary(wasmUrl, wasm);
            wasmDownloaded = true;
        }

        let execResult = await fetchWasmExecResolved(execUrl, wasmExec, prev);
        if (!execResult.downloaded) {
            console.log("fetch-micron-wasm: wasm_exec.js unchanged (304 Not Modified), skipping download.");
        } else if (prev?.wasmExecEtag && prev?.wasmExecSourceUrl === execUrl) {
            console.log("fetch-micron-wasm: wasm_exec.js updated from upstream.");
        } else {
            console.log("fetch-micron-wasm: wasm_exec.js downloaded.");
        }

        const downloads = [];
        if (wasmDownloaded) downloads.push(WASM_FILENAME);
        if (execResult.downloaded) downloads.push("wasm_exec.js");
        if (downloads.length === 0) {
            console.log("fetch-micron-wasm: OK (no downloads; artifacts match upstream).");
        } else {
            console.log(`fetch-micron-wasm: OK (${wasmResult.size} bytes WASM; fetched: ${downloads.join(", ")})`);
        }

        const integrity = {
            version: MICRON_PARSER_GO_RELEASE_TAG,
            wasm: wasmResult.sri,
            wasmExec: execResult.sri,
            wasmExecSourceUrl: execUrl,
        };
        if (execResult.etag) {
            integrity.wasmExecEtag = execResult.etag;
        }
        const nextIntegrityJson = JSON.stringify(integrity, null, 2);
        const prevIntegrityRaw =
            fs.existsSync(integrityPath) && fs.statSync(integrityPath).isFile()
                ? fs.readFileSync(integrityPath, "utf8")
                : null;
        if (prevIntegrityRaw !== nextIntegrityJson) {
            fs.writeFileSync(integrityPath, nextIntegrityJson);
            console.log("fetch-micron-wasm: SRI hashes written to integrity.json");
        } else {
            console.log("fetch-micron-wasm: integrity.json unchanged.");
        }
    } catch (e) {
        console.warn("fetch-micron-wasm: failed:", e?.message || e);
        if (passedShasumsFetch) {
            rmQuiet(wasm);
            rmQuiet(wasmExec);
            rmQuiet(integrityPath);
        }
        process.exit(0);
    }
}

main();
