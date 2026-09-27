// SPDX-License-Identifier: 0BSD
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
    appendDownloadChunk,
    bytesToBase64,
    consumeDownloadChunksAsBase64,
    consumeDownloadChunksAsText,
    createPageDownloadPayload,
    createCancelDownloadPayload,
    createFileDownloadPayload,
    createArchivesGetPayload,
    createArchiveLoadPayload,
    discardDownloadChunks,
    sendNomadWs,
    NOMAD_DOWNLOAD_BUFFER_MAX_BYTES,
} from "../../meshchatx/src/frontend/features/nomadnetwork/lib/nomadPageDownloads.ts";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection.ts";

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection.ts", () => ({
    default: {
        send: vi.fn(() => true),
    },
}));

describe("nomadPageDownloads contract", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("uses page_path for page downloads", () => {
        const payload = createPageDownloadPayload("aabbccddeeff00112233445566778899", "/page/index.mu", true);
        expect(payload.type).toBe("nomadnet.page.download");
        expect(payload.nomadnet_page_download.page_path).toBe("/page/index.mu");
        expect(payload.nomadnet_page_download.private).toBe(true);
        expect(payload.nomadnet_page_download.path).toBeUndefined();
    });

    it("uses file_path for file downloads", () => {
        const payload = createFileDownloadPayload("aabbccddeeff00112233445566778899", "/file/a.bin");
        expect(payload.type).toBe("nomadnet.file.download");
        expect(payload.nomadnet_file_download.file_path).toBe("/file/a.bin");
        expect(payload.nomadnet_file_download.path).toBeUndefined();
    });

    it("cancels with top-level download_id", () => {
        expect(createCancelDownloadPayload(7)).toEqual({
            type: "nomadnet.download.cancel",
            download_id: 7,
        });
    });

    it("attaches a top-level request_id when supplied", () => {
        const page = createPageDownloadPayload(
            "aabbccddeeff00112233445566778899",
            "/page/a.mu",
            false,
            1,
            null,
            "np-3"
        );
        expect(page.request_id).toBe("np-3");
        const file = createFileDownloadPayload(
            "aabbccddeeff00112233445566778899",
            "/file/a.bin",
            false,
            false,
            null,
            "nf-4"
        );
        expect(file.request_id).toBe("nf-4");
        const bare = createPageDownloadPayload("aabbccddeeff00112233445566778899", "/page/a.mu");
        expect(bare.request_id).toBeUndefined();
    });

    it("builds archives get and load payloads", () => {
        expect(createArchivesGetPayload("aa", "/page/index.mu")).toEqual({
            type: "nomadnet.page.archives.get",
            destination_hash: "aa",
            page_path: "/page/index.mu",
        });
        expect(createArchiveLoadPayload(3, 99)).toEqual({
            type: "nomadnet.page.archive.load",
            archive_id: 3,
            download_id: 99,
        });
    });

    it("stringifies before WebSocketConnection.send", () => {
        sendNomadWs({ type: "nomadnet.page.archives.get", destination_hash: "aa", page_path: "/p" });
        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({ type: "nomadnet.page.archives.get", destination_hash: "aa", page_path: "/p" })
        );
    });
});

describe("nomad chunk reassembly", () => {
    it("reassembles page chunks as utf-8 text", () => {
        const buffers = {};
        const text = "Hello Nomad chunked page";
        const bytes = new TextEncoder().encode(text);
        const mid = Math.floor(bytes.length / 2);
        appendDownloadChunk(buffers, 42, { chunk_b64: bytesToBase64(bytes.slice(0, mid)) });
        appendDownloadChunk(buffers, 42, { chunk_b64: bytesToBase64(bytes.slice(mid)) });
        expect(consumeDownloadChunksAsText(buffers, 42)).toBe(text);
        expect(buffers[42]).toBeUndefined();
    });

    it("reassembles file chunks as base64", () => {
        const buffers = {};
        const payload = new Uint8Array([0, 1, 2, 250, 255]);
        appendDownloadChunk(buffers, "f1", { chunk_b64: bytesToBase64(payload.slice(0, 2)) });
        appendDownloadChunk(buffers, "f1", { chunk_b64: bytesToBase64(payload.slice(2)) });
        expect(consumeDownloadChunksAsBase64(buffers, "f1")).toBe(bytesToBase64(payload));
        expect(buffers.f1).toBeUndefined();
    });

    it("discards incomplete chunk buffers", () => {
        const buffers = {};
        appendDownloadChunk(buffers, 9, { chunk_b64: bytesToBase64(new Uint8Array([1, 2])) });
        discardDownloadChunks(buffers, 9);
        expect(buffers[9]).toBeUndefined();
        expect(consumeDownloadChunksAsText(buffers, 9)).toBe("");
    });

    it("drops buffers once a transfer exceeds the byte cap", () => {
        const buffers = {};
        const nearCap = new Uint8Array(NOMAD_DOWNLOAD_BUFFER_MAX_BYTES);
        appendDownloadChunk(buffers, 5, { chunk_b64: bytesToBase64(nearCap) });
        expect(buffers[5]).toBeDefined();
        appendDownloadChunk(buffers, 5, { chunk_b64: bytesToBase64(new Uint8Array([1])) });
        expect(buffers[5]).toBeUndefined();
    });
});
