import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "fs";
import { createHash } from "crypto";
import path from "path";

const REPO_ROOT = path.resolve(__dirname, "../..");

function computeSri384(filePath) {
    const buf = readFileSync(filePath);
    const hash = createHash("sha384").update(buf).digest("base64");
    return `sha384-${hash}`;
}

describe("SRI (Subresource Integrity) Verification", () => {
    describe("micron-parser-go WASM", () => {
        it("has valid integrity.json with matching SRI hashes", () => {
            const integrityPath = path.join(
                REPO_ROOT,
                "meshchatx/src/frontend/public/vendor/micron-parser-go/integrity.json"
            );
            const wasmPath = path.join(
                REPO_ROOT,
                "meshchatx/src/frontend/public/vendor/micron-parser-go/micron-parser-go.wasm"
            );
            const execPath = path.join(REPO_ROOT, "meshchatx/src/frontend/public/vendor/micron-parser-go/wasm_exec.js");

            if (!existsSync(integrityPath)) {
                return; // Skip if WASM not fetched
            }

            const integrity = JSON.parse(readFileSync(integrityPath, "utf-8"));
            expect(integrity.version).toBeTruthy();
            expect(integrity.wasm).toMatch(/^sha384-[A-Za-z0-9+/=]+$/);
            expect(integrity.wasmExec).toMatch(/^sha384-[A-Za-z0-9+/=]+$/);

            if (existsSync(wasmPath)) {
                const actualWasmHash = computeSri384(wasmPath);
                expect(actualWasmHash).toBe(integrity.wasm);
            }

            if (existsSync(execPath)) {
                const actualExecHash = computeSri384(execPath);
                expect(actualExecHash).toBe(integrity.wasmExec);
            }
        });
    });

    describe("Codec2 Emscripten", () => {
        it("has valid integrity.json with all required files", () => {
            const integrityPath = path.join(
                REPO_ROOT,
                "meshchatx/src/frontend/public/assets/js/codec2-emscripten/integrity.json"
            );
            const baseDir = path.join(REPO_ROOT, "meshchatx/src/frontend/public/assets/js/codec2-emscripten");

            expect(existsSync(integrityPath)).toBe(true);

            const integrity = JSON.parse(readFileSync(integrityPath, "utf-8"));
            expect(integrity.version).toBeTruthy();
            expect(integrity.files).toBeTruthy();

            const requiredFiles = [
                "c2dec.wasm",
                "c2dec.js",
                "c2enc.wasm",
                "c2enc.js",
                "sox.wasm",
                "sox.js",
                "codec2-lib.js",
                "codec2-microphone-recorder.js",
                "processor.js",
                "wav-encoder.js",
            ];

            for (const file of requiredFiles) {
                expect(integrity.files[file]).toMatch(/^sha384-[A-Za-z0-9+/=]+$/);

                const filePath = path.join(baseDir, file);
                if (existsSync(filePath)) {
                    const actualHash = computeSri384(filePath);
                    expect(actualHash).toBe(integrity.files[file]);
                }
            }
        });
    });

    describe("RNode Flasher", () => {
        it("has valid integrity.json with all required vendor libraries", () => {
            const integrityPath = path.join(REPO_ROOT, "meshchatx/src/frontend/public/rnode-flasher/js/integrity.json");
            const baseDir = path.join(REPO_ROOT, "meshchatx/src/frontend/public/rnode-flasher/js");

            expect(existsSync(integrityPath)).toBe(true);

            const integrity = JSON.parse(readFileSync(integrityPath, "utf-8"));
            expect(integrity.version).toBeTruthy();
            expect(integrity.files).toBeTruthy();

            const requiredFiles = [
                "zip.min.js",
                "crypto-js@3.9.1-1/core.js",
                "crypto-js@3.9.1-1/md5.js",
                "esptool-js@0.4.5/bundle.js",
                "nrf52_dfu_flasher.js",
                "rnode.js",
                "web-serial-polyfill@1.0.15/dist/serial.js",
            ];

            for (const file of requiredFiles) {
                expect(integrity.files[file]).toMatch(/^sha384-[A-Za-z0-9+/=]+$/);

                const filePath = path.join(baseDir, file);
                if (existsSync(filePath)) {
                    const actualHash = computeSri384(filePath);
                    expect(actualHash).toBe(integrity.files[file]);
                }
            }
        });
    });

    describe("SRI hash format validation", () => {
        it("all SRI hashes use sha384- prefix and base64 format", async () => {
            const integrityFiles = [
                "meshchatx/src/frontend/public/vendor/micron-parser-go/integrity.json",
                "meshchatx/src/frontend/public/assets/js/codec2-emscripten/integrity.json",
                "meshchatx/src/frontend/public/rnode-flasher/js/integrity.json",
            ];

            for (const relPath of integrityFiles) {
                const fullPath = path.join(REPO_ROOT, relPath);
                if (!existsSync(fullPath)) continue;

                const data = JSON.parse(readFileSync(fullPath, "utf-8"));
                const hashes =
                    data.wasm && data.wasmExec ? [data.wasm, data.wasmExec] : Object.values(data.files || {});

                for (const hash of hashes) {
                    expect(hash).toMatch(/^sha384-[A-Za-z0-9+/=]+$/);
                    // SHA-384 in base64 should be exactly 64 characters
                    const b64Part = hash.replace("sha384-", "");
                    expect(b64Part.length).toBe(64);
                }
            }
        });
    });
});
