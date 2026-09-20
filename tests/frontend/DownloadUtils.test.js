import { describe, it, expect, vi, afterEach } from "vitest";
import DownloadUtils from "@/js/DownloadUtils";

describe("DownloadUtils", () => {
    afterEach(() => {
        delete window.MeshChatXAndroid;
        vi.restoreAllMocks();
    });

    it("delegates base64 saves to Android bridge when present", () => {
        const saveDownload = vi.fn();
        window.MeshChatXAndroid = { saveDownload };
        DownloadUtils.downloadFromBase64("test.mu", "QUJD");
        expect(saveDownload).toHaveBeenCalledWith("test.mu", "QUJD");
    });

    it("downloadFile uses Android bridge when present", async () => {
        const saveDownload = vi.fn();
        window.MeshChatXAndroid = { saveDownload };
        const blob = new Blob([new Uint8Array([1, 2, 3])]);
        await DownloadUtils.downloadFile("f.bin", blob);
        expect(saveDownload).toHaveBeenCalledTimes(1);
        const [name, b64] = saveDownload.mock.calls[0];
        expect(name).toBe("f.bin");
        expect(typeof b64).toBe("string");
        expect(b64.length).toBeGreaterThan(0);
    });

    it("parseFilenameFromContentDisposition prefers UTF-8 filename*", () => {
        const header = "attachment; filename=\"fallback.bin\"; filename*=UTF-8''photo%2Epng";
        expect(DownloadUtils.parseFilenameFromContentDisposition(header, "default.bin")).toBe("photo.png");
    });

    it("downloadFromApiResponse uses Android bridge when present", async () => {
        const saveDownload = vi.fn();
        window.MeshChatXAndroid = { saveDownload };
        await DownloadUtils.downloadFromApiResponse(
            {
                data: new Uint8Array([9, 8, 7]),
                headers: {
                    "content-disposition": 'attachment; filename="backup.zip"',
                    "content-type": "application/zip",
                },
            },
            "fallback.zip"
        );
        expect(saveDownload).toHaveBeenCalledWith("backup.zip", expect.any(String));
    });

    it("uses saveDownloadWithId when a downloadId is supplied", async () => {
        const saveDownload = vi.fn();
        const saveDownloadWithId = vi.fn();
        window.MeshChatXAndroid = { saveDownload, saveDownloadWithId };
        DownloadUtils.downloadFromBase64("tracked.bin", "QUJD", { downloadId: "dl-7" });
        expect(saveDownloadWithId).toHaveBeenCalledWith("dl-7", "tracked.bin", "QUJD");
        expect(saveDownload).not.toHaveBeenCalled();
    });

    it("falls back to saveDownload when tracked save is missing", async () => {
        const saveDownload = vi.fn();
        window.MeshChatXAndroid = { saveDownload };
        DownloadUtils.downloadFromBase64("tracked.bin", "QUJD", { downloadId: "dl-7" });
        expect(saveDownload).toHaveBeenCalledWith("tracked.bin", "QUJD");
    });

    it("sends large base64 payloads through the chunked bridge", async () => {
        const begin = vi.fn(() => "save-1");
        const append = vi.fn(() => true);
        const finish = vi.fn(() => true);
        const saveDownload = vi.fn();
        window.MeshChatXAndroid = {
            saveDownload,
            saveDownloadBegin: begin,
            saveDownloadAppend: append,
            saveDownloadFinish: finish,
            saveDownloadAbort: vi.fn(),
        };
        const payload = "A".repeat(5 * 1024 * 1024);
        DownloadUtils.downloadFromBase64("big.bin", payload, { downloadId: "dl-9" });
        expect(begin).toHaveBeenCalledWith("big.bin");
        expect(append.mock.calls.length).toBeGreaterThan(1);
        for (const [, chunk] of append.mock.calls) {
            expect(chunk.length % 4).toBe(0);
        }
        expect(saveDownload).not.toHaveBeenCalled();
    });

    it("aborts the chunked save when an append fails", async () => {
        const begin = vi.fn(() => "save-2");
        const append = vi.fn(() => false);
        const abort = vi.fn();
        window.MeshChatXAndroid = {
            saveDownload: vi.fn(),
            saveDownloadBegin: begin,
            saveDownloadAppend: append,
            saveDownloadFinish: vi.fn(() => true),
            saveDownloadAbort: abort,
        };
        const payload = "A".repeat(5 * 1024 * 1024);
        expect(() => DownloadUtils.downloadFromBase64("big.bin", payload)).toThrow("saveDownloadAppend failed");
        expect(abort).toHaveBeenCalledWith("save-2");
    });

    it("downloadFile chunks large blobs over the bridge", async () => {
        const begin = vi.fn(() => "save-3");
        const append = vi.fn(() => true);
        const finish = vi.fn(() => true);
        const finishWithId = vi.fn(() => true);
        window.MeshChatXAndroid = {
            saveDownload: vi.fn(),
            saveDownloadBegin: begin,
            saveDownloadAppend: append,
            saveDownloadFinish: finish,
            saveDownloadFinishWithId: finishWithId,
            saveDownloadAbort: vi.fn(),
        };
        const blob = new Blob([new Uint8Array(5 * 1024 * 1024)]);
        await DownloadUtils.downloadFile("blob.bin", blob, { downloadId: "dl-11" });
        expect(begin).toHaveBeenCalledWith("blob.bin");
        expect(append.mock.calls.length).toBeGreaterThan(1);
        expect(finishWithId).toHaveBeenCalledWith("save-3", "dl-11");
        expect(finish).not.toHaveBeenCalled();
    });

    it("downloadFile triggers anchor download when Android bridge is absent", async () => {
        const click = vi.fn();
        const append = vi.fn();
        const remove = vi.fn();
        const link = { click, remove, download: "", href: "", style: { display: "" } };
        vi.spyOn(document, "createElement").mockReturnValue(link);
        vi.spyOn(document.body, "append").mockImplementation(append);
        URL.createObjectURL = vi.fn(() => "blob:mock");

        await DownloadUtils.downloadFile("browser.bin", new Blob([new Uint8Array([1])]));

        expect(click).toHaveBeenCalledTimes(1);
        expect(link.download).toBe("browser.bin");
        expect(link.href).toBe("blob:mock");
        expect(append).toHaveBeenCalledWith(link);
        expect(remove).toHaveBeenCalledTimes(1);
    });

    it("downloadFromApiResponse reads Fetch Headers via .get()", async () => {
        const saveDownload = vi.fn();
        window.MeshChatXAndroid = { saveDownload };
        const headers = new Headers({
            "content-disposition": 'attachment; filename="from-headers.zip"',
            "content-type": "application/zip",
        });
        await DownloadUtils.downloadFromApiResponse(
            {
                data: new Uint8Array([1]),
                headers,
            },
            "fallback.zip"
        );
        expect(saveDownload).toHaveBeenCalledWith("from-headers.zip", expect.any(String));
    });

    it("headerValue works for plain objects and Headers", () => {
        expect(DownloadUtils.headerValue({ "Content-Type": "text/plain" }, "content-type")).toBe("text/plain");
        expect(DownloadUtils.headerValue(new Headers({ "content-type": "a/b" }), "Content-Type")).toBe("a/b");
    });
});
