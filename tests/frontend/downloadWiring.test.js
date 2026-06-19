import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AboutPage from "@/components/about/AboutPage.vue";
import IdentitiesPage from "@/components/settings/IdentitiesPage.vue";
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
                if (String(url).includes("/database/backup/download")) {
                    return Promise.resolve({
                        data: new ArrayBuffer(4),
                        headers: { "content-disposition": 'attachment; filename="meshchatx-backup.zip"' },
                    });
                }
                if (String(url).includes("/database/backups/")) {
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
                return Promise.resolve({ data: {}, headers: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
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

    it("AboutPage.backupDatabase saves through DownloadUtils instead of anchor click", async () => {
        const wrapper = mount(AboutPage, {
            global: {
                mocks: { $t: (key) => key },
                stubs: { MaterialDesignIcon: true },
            },
        });

        await wrapper.vm.backupDatabase();

        expect(axiosMock.get).toHaveBeenCalledWith(
            "/api/v1/database/backup/download",
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

    it("AboutPage.downloadBackupFile saves through DownloadUtils", async () => {
        const wrapper = mount(AboutPage, {
            global: {
                mocks: { $t: (key) => key },
                stubs: { MaterialDesignIcon: true },
            },
        });

        await wrapper.vm.downloadBackupFile("auto-backup.zip");

        expect(DownloadUtils.downloadFromApiResponse).toHaveBeenCalledWith(
            expect.objectContaining({ data: expect.any(ArrayBuffer) }),
            "auto-backup.zip"
        );
        expect(ToastUtils.success).toHaveBeenCalled();
    });

    it("IdentitiesPage.downloadIdentityFile saves through DownloadUtils", async () => {
        const wrapper = mount(IdentitiesPage, {
            global: {
                mocks: { $t: (key) => key },
                stubs: { MaterialDesignIcon: true, LxmfUserIcon: true },
            },
        });

        await wrapper.vm.downloadIdentityFile();

        expect(DownloadUtils.downloadFromApiResponse).toHaveBeenCalledWith(
            expect.objectContaining({ data: expect.any(ArrayBuffer) }),
            "identity"
        );
    });
});
