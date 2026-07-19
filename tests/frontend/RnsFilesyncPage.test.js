import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RnsFilesyncPage from "@/components/filesync/RnsFilesyncPage.vue";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/registries/wsEventRegistry.js", () => ({
    onWsEvent: vi.fn(),
    offWsEvent: vi.fn(),
}));

describe("RnsFilesyncPage.vue", () => {
    let apiMock;

    beforeEach(() => {
        apiMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
        };
        window.api = apiMock;

        apiMock.get.mockImplementation((url) => {
            if (url === "/api/v1/filesync/status") {
                return Promise.resolve({
                    data: {
                        running: false,
                        sync_directory: "/tmp/sync",
                        peers: 0,
                        files: 0,
                        monitor: true,
                        announce_interval: 300,
                    },
                });
            }
            if (url === "/api/v1/filesync/peers") {
                return Promise.resolve({ data: { peers: [] } });
            }
            if (url === "/api/v1/filesync/files") {
                return Promise.resolve({ data: { files: [] } });
            }
            if (url === "/api/v1/filesync/acl") {
                return Promise.resolve({ data: { enforce: false, rules: {} } });
            }
            return Promise.resolve({ data: {} });
        });
        apiMock.post.mockResolvedValue({ data: { ok: true } });
        apiMock.patch.mockResolvedValue({ data: { ok: true } });
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountPage = () =>
        mount(RnsFilesyncPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                    ToolsPageHeader: {
                        template: "<div class='header-stub'>{{ title }}</div>",
                        props: ["title", "description", "eyebrow", "icon", "accent"],
                    },
                },
            },
        });

    it("renders and loads status", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(apiMock.get).toHaveBeenCalledWith("/api/v1/filesync/status"));
        expect(wrapper.text()).toContain("rns_filesync.title");
        expect(wrapper.vm.syncDirectory).toBe("/tmp/sync");
    });

    it("starts filesync and toasts success", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        await wrapper.vm.startService();
        expect(apiMock.post).toHaveBeenCalledWith(
            "/api/v1/filesync/start",
            expect.objectContaining({
                sync_directory: "/tmp/sync",
                monitor: true,
            })
        );
        expect(ToastUtils.success).toHaveBeenCalledWith("rns_filesync.started");
    });

    it("shows error toast when connect fails", async () => {
        apiMock.post.mockRejectedValueOnce(new Error("path timeout"));
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        wrapper.vm.status.running = true;
        wrapper.vm.connectHash = "ab".repeat(16);
        await wrapper.vm.connectPeer();
        expect(ToastUtils.error).toHaveBeenCalled();
    });

    it("browses and downloads a remote file", async () => {
        apiMock.post.mockImplementation((url) => {
            if (url === "/api/v1/filesync/browse") {
                return Promise.resolve({
                    data: { ok: true, files: [{ path: "notes.txt", size: 12 }] },
                });
            }
            return Promise.resolve({ data: { ok: true } });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        wrapper.vm.status.running = true;
        wrapper.vm.browsePeerId = "cd".repeat(16);
        await wrapper.vm.browsePeer();
        expect(wrapper.vm.remoteFiles).toEqual([{ path: "notes.txt", size: 12 }]);
        await wrapper.vm.downloadFile("notes.txt");
        expect(apiMock.post).toHaveBeenCalledWith("/api/v1/filesync/download", {
            peer_id: "cd".repeat(16),
            path: "notes.txt",
        });
        expect(ToastUtils.info).toHaveBeenCalledWith("rns_filesync.download_started");
    });
});
