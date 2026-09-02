import { describe, it, expect } from "vitest";
import {
    isWasmUploadFile,
    pickWasmFileFromClipboardEvent,
    pickWasmFileFromDataTransfer,
    pickWasmFileFromFileList,
} from "../../meshchatx/src/frontend/js/micronWasmUpload.js";

describe("micronWasmUpload", () => {
    it("accepts .wasm filenames and wasm mime types", () => {
        expect(isWasmUploadFile(new File([], "micron-parser-go-v1.0.7.wasm"))).toBe(true);
        expect(isWasmUploadFile(new File([], "blob.bin", { type: "application/wasm" }))).toBe(true);
        expect(isWasmUploadFile(new File([], "notes.txt"))).toBe(false);
    });

    it("picks wasm from file lists and data transfer", () => {
        const wasm = new File([], "test.wasm", { type: "application/wasm" });
        const other = new File([], "notes.txt", { type: "text/plain" });
        expect(pickWasmFileFromFileList([other, wasm])).toBe(wasm);
        expect(
            pickWasmFileFromDataTransfer({
                files: [other, wasm],
                items: [],
            })
        ).toBe(wasm);
    });

    it("picks wasm from clipboard paste events", () => {
        const wasm = new File([], "test.wasm", { type: "application/wasm" });
        expect(
            pickWasmFileFromClipboardEvent({
                clipboardData: {
                    files: [wasm],
                    items: [],
                },
            })
        ).toBe(wasm);
    });
});
