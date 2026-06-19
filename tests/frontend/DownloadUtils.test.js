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
});
