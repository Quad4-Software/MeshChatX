import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { backupDatabase, downloadBackupFile } from "@/features/about/lib/backupApi.ts";
import IdentitiesPage from "@/features/settings/components/IdentitiesPage.svelte";
import DownloadUtils from "@/js/DownloadUtils";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/DownloadUtils", () => ({
    default: {
        downloadFromApiResponse: vi.fn(() => Promise.resolve()),
        downloadFile: vi.fn(() => Promise.resolve()),
        downloadFromBase64: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe("download wiring through DownloadUtils", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (String(url).includes("/database/backups/")) {
                    return Promise.resolve({
                        data: new ArrayBuffer(8),
                        headers: {},
                    });
                }
                return Promise.resolve({ data: {}, headers: {} });
            }),
            post: vi.fn().mockImplementation((url) => {
                if (String(url).includes("/database/backup/download")) {
                    return Promise.resolve({
                        data: new ArrayBuffer(4),
                        headers: { "content-disposition": 'attachment; filename="meshchatx-backup.zip"' },
                    });
                }
                if (String(url).includes("/database/backups/") && String(url).includes("/download")) {
                    return Promise.resolve({
                        data: new ArrayBuffer(8),
                        headers: {},
                    });
                }
                if (String(url).includes("/identity/backup/download")) {
                    return Promise.resolve({
                        data: new ArrayBuffer(2),
                        headers: {},
                    });
                }
                if (String(url).includes("/identities/export-all")) {
                    return Promise.resolve({
                        data: new ArrayBuffer(3),
                        headers: {},
                    });
                }
                if (String(url).includes("/api/v1/bots/export")) {
                    return Promise.resolve({
                        data: new ArrayBuffer(5),
                        headers: {
                            "content-disposition": 'attachment; filename="bot_bot1_identity"',
                        },
                    });
                }
                return Promise.resolve({ data: {}, headers: {} });
            }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
        window.electron = {
            getMemoryUsage: vi.fn().mockResolvedValue(null),
            electronVersion: vi.fn().mockReturnValue("1.0.0"),
            chromeVersion: vi.fn().mockReturnValue("1.0.0"),
            nodeVersion: vi.fn().mockReturnValue("1.0.0"),
            appVersion: vi.fn().mockResolvedValue("1.0.0"),
        };
    });

    afterEach(() => {
        delete window.api;
        delete window.electron;
    });

    it("About backupDatabase saves through DownloadUtils instead of anchor click", async () => {
        await backupDatabase();

        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/database/backup/download",
            null,
            expect.objectContaining({ responseType: "arraybuffer" })
        );
        expect(DownloadUtils.downloadFromApiResponse).toHaveBeenCalledWith(
            expect.objectContaining({
                headers: expect.objectContaining({
                    "content-disposition": expect.stringContaining("meshchatx-backup.zip"),
                }),
            }),
            "meshchatx-backup.zip"
        );
    });

    it("About downloadBackupFile saves through DownloadUtils", async () => {
        await downloadBackupFile("auto-backup.zip");

        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/database/backups/auto-backup.zip/download",
            null,
            expect.objectContaining({ responseType: "arraybuffer" })
        );
        expect(DownloadUtils.downloadFromApiResponse).toHaveBeenCalledWith(
            expect.objectContaining({ data: expect.any(ArrayBuffer) }),
            "auto-backup.zip"
        );
        expect(ToastUtils.success).toHaveBeenCalled();
    });

    it("IdentitiesPage.downloadIdentityFile saves through DownloadUtils", async () => {
        axiosMock.get = vi.fn().mockResolvedValue({
            data: {
                identities: [
                    {
                        hash: "hash1",
                        display_name: "Identity 1",
                        is_current: true,
                        lxmf_address: "a1b2c3d4e5f6",
                    },
                ],
            },
        });

        const { findByText } = render(IdentitiesPage);
        const exportBtn = await findByText("identities.export_key_file");
        await fireEvent.click(exportBtn);

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith(
                "/api/v1/identity/backup/download",
                {},
                expect.objectContaining({ responseType: "arraybuffer" })
            );
            expect(DownloadUtils.downloadFromApiResponse).toHaveBeenCalledWith(
                expect.objectContaining({ data: expect.any(ArrayBuffer) }),
                "identity.bin"
            );
        });
    });
});
