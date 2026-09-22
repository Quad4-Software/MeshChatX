/**
 * Render worker: runs the string-to-string parse stages off the main thread.
 *
 * Jobs:
 *   { kind: "micron-wasm", markup, darkTheme, forceMonospace }
 *     Splits markup into mu segments, converts each via micron-parser-go WASM
 *     loaded inside this worker, and returns raw (unsanitized) HTML per
 *     segment plus partial lines the main thread must render itself.
 *     Sanitization intentionally stays on the main thread where DOMPurify
 *     runs against the real DOM.
 *   { kind: "markdown", markdown }
 *     marked.parse only; the caller sanitizes the returned HTML.
 *
 * The worker is a classic (iife) bundle so importScripts can load the
 * vendored wasm_exec.js. The exec runtime is fetched, SHA-384 verified
 * against the build's integrity.json, then imported via a blob URL so the
 * verified bytes are what actually execute.
 */

import { marked } from "marked";
import { splitMicronWasmSegments } from "../micronSegments.js";

declare function importScripts(...urls: string[]): void;

marked.setOptions({
    gfm: true,
    breaks: true,
});

type WorkerSegment =
    | { type: "html"; html: string }
    | { type: "partial"; line: string };

let wasmReadyPromise: Promise<void> | null = null;

function vendorBaseUrl(): string {
    const root: string = import.meta.env?.BASE_URL || "/";
    return `${root.replace(/\/?$/, "/")}vendor/micron-parser-go`;
}

async function sha384Base64(buf: ArrayBuffer): Promise<string> {
    const hash = await crypto.subtle.digest("SHA-384", buf);
    const bytes = new Uint8Array(hash);
    let bin = "";
    for (let i = 0; i < bytes.length; i += 1) {
        bin += String.fromCharCode(bytes[i]);
    }
    return `sha384-${btoa(bin)}`;
}

async function verifySri(buf: ArrayBuffer, expectedHash: string | undefined, name: string) {
    if (!expectedHash) {
        throw new Error(`micron worker: missing SRI hash for ${name}`);
    }
    const actual = await sha384Base64(buf);
    if (actual !== expectedHash) {
        throw new Error(`micron worker: SRI mismatch for ${name}`);
    }
}

async function initWasm(): Promise<void> {
    const g = globalThis as any;
    if (typeof g.micronConvert === "function") {
        return;
    }
    const base = vendorBaseUrl();
    const integrityRes = await fetch(`${base}/integrity.json`);
    if (!integrityRes.ok) {
        throw new Error(`micron worker: integrity.json fetch failed (${integrityRes.status})`);
    }
    const integrity = await integrityRes.json();
    if (!integrity?.wasm || !integrity?.wasmExec) {
        throw new Error("micron worker: integrity.json missing hashes");
    }

    const execRes = await fetch(`${base}/wasm_exec.js`);
    if (!execRes.ok) {
        throw new Error(`micron worker: wasm_exec.js fetch failed (${execRes.status})`);
    }
    const execBuf = await execRes.arrayBuffer();
    await verifySri(execBuf, integrity.wasmExec, "wasm_exec.js");
    // Verified bytes execute via blob URL; worker-src blob: is in CSP.
    const blobUrl = URL.createObjectURL(new Blob([execBuf], { type: "text/javascript" }));
    try {
        importScripts(blobUrl);
    } finally {
        URL.revokeObjectURL(blobUrl);
    }
    if (typeof g.Go === "undefined") {
        throw new Error("micron worker: Go runtime missing after wasm_exec.js");
    }

    const wasmRes = await fetch(`${base}/micron-parser-go.wasm`);
    if (!wasmRes.ok) {
        throw new Error(`micron worker: wasm fetch failed (${wasmRes.status})`);
    }
    const wasmBuf = await wasmRes.arrayBuffer();
    await verifySri(wasmBuf, integrity.wasm, "micron-parser-go.wasm");

    const go = new g.Go();
    let result;
    try {
        result = await WebAssembly.instantiateStreaming(
            new Response(wasmBuf, { headers: { "content-type": "application/wasm" } }),
            go.importObject,
        );
    } catch {
        result = await WebAssembly.instantiate(wasmBuf, go.importObject);
    }
    go.run(result.instance);
    if (typeof g.micronConvert !== "function") {
        throw new Error("micron worker: micronConvert was not registered");
    }
}

function handleMicronWasm(msg: any): WorkerSegment[] {
    const g = globalThis as any;
    const out: WorkerSegment[] = [];
    for (const seg of splitMicronWasmSegments(msg.markup)) {
        if (seg.type === "mu") {
            out.push({
                type: "html",
                html: String(
                    g.micronConvert(seg.text, msg.darkTheme === true, msg.forceMonospace === true),
                ),
            });
        } else {
            out.push({ type: "partial", line: seg.line });
        }
    }
    return out;
}

self.onmessage = async (event: MessageEvent) => {
    const msg = event.data || {};
    const id = msg.id;
    try {
        if (msg.kind === "micron-wasm") {
            wasmReadyPromise = wasmReadyPromise ?? initWasm();
            await wasmReadyPromise;
            const segments = handleMicronWasm(msg);
            (self as any).postMessage({ id, ok: true, segments });
            return;
        }
        if (msg.kind === "markdown") {
            const html = marked.parse(String(msg.markdown ?? ""));
            (self as any).postMessage({ id, ok: true, html });
            return;
        }
        throw new Error(`micron worker: unknown job kind ${String(msg.kind)}`);
    } catch (e: any) {
        // A failed wasm init should not poison later jobs; retry next time.
        if (msg.kind === "micron-wasm") {
            wasmReadyPromise = null;
        }
        (self as any).postMessage({
            id,
            ok: false,
            error: String(e?.message ?? e ?? "unknown worker error"),
        });
    }
};
