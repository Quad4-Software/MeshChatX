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

vi.mock("@/js/ElectronUtils", () => ({
    default: {
        openDirectoryOrCopy: vi.fn().mockResolvedValue(true),
        isElectron: vi.fn().mockReturnValue(false),
        pickDirectory: vi.fn().mockResolvedValue(null),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

vi.mock("@/js/DownloadUtils", () => ({
    default: {
        downloadFromApiResponse: vi.fn().mockResolvedValue(undefined),
    },
}));

describe("RnsFilesyncPage.vue", () => {
    let apiMock;

    beforeEach(() => {
        apiMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
            delete: vi.fn(),
        };
        window.api = apiMock;

        apiMock.get.mockImplementation((url) => {
            if (url === "/api/v1/filesync/status") {
                return Promise.resolve({
                    data: {
                        running: false,
                        sync_directory: "/tmp/sync",
                        storage_directory: "/tmp",
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
            if (url === "/api/v1/filesync/tree") {
                return Promise.resolve({
                    data: {
                        ok: true,
                        current: "",
                        parent: null,
                        entries: [{ name: "hello.txt", path: "hello.txt", type: "file", size: 4 }],
                    },
                });
            }
            if (url === "/api/v1/filesync/files") {
                return Promise.resolve({ data: { files: [] } });
            }
            if (url === "/api/v1/filesync/acl") {
                return Promise.resolve({ data: { enforce: false, rules: {} } });
            }
            if (String(url).startsWith("/api/v1/filesync/directories")) {
                return Promise.resolve({
                    data: {
                        ok: true,
                        root: "/tmp",
                        current: "/tmp/sync",
                        parent: "/tmp",
                        directories: [{ name: "docs", path: "/tmp/sync/docs" }],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
        apiMock.post.mockResolvedValue({ data: { ok: true } });
        apiMock.patch.mockResolvedValue({ data: { ok: true } });
        apiMock.delete.mockResolvedValue({ data: { ok: true } });
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
                    FilesyncDirectoryBrowserModal: {
                        template: "<div class='browser-stub' v-if='open'></div>",
                        props: ["open", "initialPath"],
                        emits: ["close", "select"],
                    },
                    FilesyncFileManager: {
                        template: "<div class='file-manager-stub'></div>",
                        props: ["syncDirectory"],
                        methods: {
                            refresh: vi.fn().mockResolvedValue(undefined),
                        },
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

    it("files tab mounts file manager", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        wrapper.vm.activeTab = "files";
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".file-manager-stub").exists()).toBe(true);
    });

    it("uses themed input-field classes", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        expect(wrapper.find("input.input-field").exists()).toBe(true);
        expect(wrapper.find("input.glass-input").exists()).toBe(false);
    });

    it("opens directory browser from browse button", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        expect(wrapper.vm.directoryBrowserOpen).toBe(false);
        await wrapper.vm.openDirectoryBrowser();
        expect(wrapper.vm.directoryBrowserOpen).toBe(true);
        wrapper.vm.onDirectorySelected("/tmp/sync/docs");
        expect(wrapper.vm.syncDirectory).toBe("/tmp/sync/docs");
        expect(ToastUtils.success).toHaveBeenCalledWith("rns_filesync.folder_selected");
    });

    it("warns when browsing while syncing", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        wrapper.vm.status.running = true;
        await wrapper.vm.openDirectoryBrowser();
        expect(wrapper.vm.directoryBrowserOpen).toBe(false);
        expect(ToastUtils.warning).toHaveBeenCalledWith("rns_filesync.stop_before_change_folder");
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

    it("builds friendly ACL rows", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        wrapper.vm.aclRules = {
            read: ["aa".repeat(16)],
            write: ["aa".repeat(16)],
            delete: [],
        };
        expect(wrapper.vm.aclRows).toHaveLength(1);
        expect(wrapper.vm.aclRows[0].permsLabel).toContain("rns_filesync.perm_read");
        expect(wrapper.vm.aclRows[0].permsLabel).toContain("rns_filesync.perm_write");
    });

    it("humanizes progress payloads", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.syncDirectory).toBe("/tmp/sync"));
        wrapper.vm.lastProgress = { path: "a.txt", status: "sending", bytes: 10, total: 100 };
        expect(wrapper.vm.lastProgressLabel).toContain("a.txt");
        expect(wrapper.vm.lastProgressLabel).toContain("sending");
    });
});

describe("FilesyncDirectoryBrowserModal.vue", () => {
    let apiMock;

    beforeEach(async () => {
        apiMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    ok: true,
                    root: "/tmp",
                    current: "/tmp/filesync",
                    parent: "/tmp",
                    directories: [{ name: "sync", path: "/tmp/filesync/sync" }],
                },
            }),
            post: vi.fn().mockResolvedValue({ data: { ok: true, path: "/tmp/filesync/new" } }),
        };
        window.api = apiMock;
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    it("loads directories when opened and selects a path", async () => {
        const { default: FilesyncDirectoryBrowserModal } =
            await import("@/components/filesync/FilesyncDirectoryBrowserModal.vue");
        const wrapper = mount(FilesyncDirectoryBrowserModal, {
            props: {
                open: true,
                initialPath: "/tmp/filesync/sync",
            },
            global: {
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: {
                        template: "<div></div>",
                        props: ["iconName"],
                    },
                },
            },
        });
        await vi.waitFor(() =>
            expect(apiMock.get).toHaveBeenCalledWith(expect.stringContaining("/api/v1/filesync/directories"))
        );
        expect(wrapper.vm.directories).toHaveLength(1);
        await wrapper.vm.confirmSelection();
        expect(wrapper.emitted("select")[0]).toEqual(["/tmp/filesync"]);
        expect(wrapper.emitted("close")).toBeTruthy();
    });
});

describe("FilesyncFileManager.vue", () => {
    let apiMock;

    beforeEach(() => {
        apiMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    ok: true,
                    current: "",
                    parent: null,
                    entries: [
                        { name: "docs", path: "docs", type: "dir" },
                        { name: "a.txt", path: "a.txt", type: "file", size: 3 },
                    ],
                },
            }),
            post: vi.fn().mockResolvedValue({ data: { ok: true, path: "a.txt" } }),
            delete: vi.fn().mockResolvedValue({ data: { ok: true } }),
        };
        window.api = apiMock;
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    it("loads tree and uploads via window.api", async () => {
        const { default: FilesyncFileManager } = await import("@/components/filesync/FilesyncFileManager.vue");
        const wrapper = mount(FilesyncFileManager, {
            props: { syncDirectory: "/tmp/sync" },
            global: {
                mocks: {
                    $t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: "<div></div>",
                        props: ["iconName"],
                    },
                },
            },
        });
        await vi.waitFor(() => expect(apiMock.get).toHaveBeenCalledWith("/api/v1/filesync/tree", expect.any(Object)));
        expect(wrapper.vm.entries).toHaveLength(2);

        await wrapper.vm.onUploadSelected({
            target: { files: [new File(["hi"], "hi.txt")], value: "x" },
        });
        expect(apiMock.post).toHaveBeenCalledWith("/api/v1/filesync/upload", expect.any(FormData));
        expect(ToastUtils.success).toHaveBeenCalledWith("rns_filesync.upload_done");
    });
});
