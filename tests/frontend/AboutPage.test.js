import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AboutPage from "@/components/about/AboutPage.vue";
import ElectronUtils from "@/js/ElectronUtils";
import DialogUtils from "@/js/DialogUtils";

describe("AboutPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        vi.useFakeTimers();
        axiosMock = {
            get: vi.fn().mockImplementation(() => Promise.resolve({ data: {} })),
            post: vi.fn().mockImplementation(() => Promise.resolve({ data: {} })),
        };
        window.api = axiosMock;
        window.URL.createObjectURL = vi.fn();
        window.URL.revokeObjectURL = vi.fn();

        // Default electron mock
        window.electron = {
            getMemoryUsage: vi.fn().mockResolvedValue(null),
            electronVersion: vi.fn().mockReturnValue("1.0.0"),
            chromeVersion: vi.fn().mockReturnValue("1.0.0"),
            nodeVersion: vi.fn().mockReturnValue("1.0.0"),
            appVersion: vi.fn().mockResolvedValue("1.0.0"),
        };
    });

    afterEach(() => {
        vi.useRealTimers();
        delete window.api;
        delete window.electron;
    });

    const mountAboutPage = () => {
        return mount(AboutPage, {
            global: {
                mocks: {
                    $t: (key, params) => {
                        if (params) {
                            return `${key} ${JSON.stringify(params)}`;
                        }
                        return key;
                    },
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });
    };

    it("fetches app info and config on mount", async () => {
        const appInfo = {
            version: "1.0.0",
            rns_version: "0.1.0",
            lxmf_version: "0.2.0",
            python_version: "3.11.0",
            reticulum_config_path: "/path/to/config",
            database_path: "/path/to/db",
            database_file_size: 1024,
            dependencies: {
                aiohttp: "3.8.1",
                cryptography: "3.4.8",
            },
        };
        const config = {
            identity_hash: "hash1",
            lxmf_address_hash: "hash2",
        };

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") return Promise.resolve({ data: { app_info: appInfo } });
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: config } });
            if (url === "/api/v1/database/health")
                return Promise.resolve({
                    data: {
                        database: {
                            quick_check: "ok",
                            journal_mode: "wal",
                            page_size: 4096,
                            page_count: 100,
                            freelist_pages: 5,
                            estimated_free_bytes: 20480,
                        },
                    },
                });
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: [] });
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        wrapper.vm.showAdvanced = true;
        await vi.runOnlyPendingTimers();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // Extra tick for multiple async calls
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/app/info");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");

        expect(wrapper.text()).toContain("MeshChatX");
        expect(wrapper.text()).toContain("Reticulum Network Stack");
        expect(wrapper.text()).toContain("hash1");
        expect(wrapper.text()).toContain("hash2");

        // Check for Dependency Chain section
        expect(wrapper.text()).toContain("Dependency Chain");
        expect(wrapper.text()).toContain("Lightweight Extensible Message Format");
        expect(wrapper.text()).toContain("Reticulum Network Stack");

        // Check for dependencies
        expect(wrapper.text()).toContain("Backend Stack");
        expect(wrapper.text()).toContain("aiohttp");
        expect(wrapper.text()).toContain("3.8.1");
    });

    it("displays Electron memory usage when running in Electron", async () => {
        vi.spyOn(ElectronUtils, "isElectron").mockReturnValue(true);
        const getMemoryUsageSpy = vi.spyOn(ElectronUtils, "getMemoryUsage").mockResolvedValue({
            private: 1000,
            residentSet: 2000,
        });

        const appInfo = {
            version: "1.0.0",
        };

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") return Promise.resolve({ data: { app_info: appInfo } });
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: {} } });
            if (url === "/api/v1/database/health") return Promise.resolve({ data: { database: {} } });
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: [] });
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        wrapper.vm.showAdvanced = true;
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(getMemoryUsageSpy).toHaveBeenCalled();
        expect(wrapper.vm.electronMemoryUsage).not.toBeNull();
        expect(wrapper.text()).toContain("Environment Information");
    });

    it("handles shutdown action", async () => {
        const confirmSpy = vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        const axiosPostSpy = axiosMock.post.mockResolvedValue({ data: { message: "Shutting down..." } });
        const shutdownSpy = vi.spyOn(ElectronUtils, "shutdown").mockImplementation(() => {});
        vi.spyOn(ElectronUtils, "isElectron").mockReturnValue(true);

        const wrapper = mountAboutPage();
        wrapper.vm.appInfo = { version: "1.0.0" };
        await wrapper.vm.$nextTick();

        await wrapper.vm.shutdown();

        expect(confirmSpy).toHaveBeenCalled();
        expect(axiosPostSpy).toHaveBeenCalledWith("/api/v1/app/shutdown");
        expect(shutdownSpy).toHaveBeenCalled();
    });

    it("updates app info periodically", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                app_info: {},
                config: {},
                database: {
                    quick_check: "ok",
                    journal_mode: "wal",
                    page_size: 4096,
                    page_count: 100,
                    freelist_pages: 5,
                    estimated_free_bytes: 20480,
                },
            },
        });
        mountAboutPage();

        expect(axiosMock.get).toHaveBeenCalledTimes(5); // info, config, health, snapshots, backups

        vi.advanceTimersByTime(5000);
        expect(axiosMock.get).toHaveBeenCalledTimes(6); // +1 from updateInterval

        vi.advanceTimersByTime(5000);
        expect(axiosMock.get).toHaveBeenCalledTimes(7); // +2 from updateInterval
    });

    it("handles vacuum database action", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                app_info: {},
                config: {},
                database: {
                    quick_check: "ok",
                    journal_mode: "wal",
                    page_size: 4096,
                    page_count: 100,
                    freelist_pages: 5,
                    estimated_free_bytes: 20480,
                },
            },
        });
        axiosMock.post.mockResolvedValue({ data: { message: "Vacuum success" } });

        const wrapper = mountAboutPage();
        await wrapper.vm.$nextTick();

        // Find vacuum button (it's the second button in the database health section)
        // Or we can just call the method directly to be sure
        await wrapper.vm.vacuumDatabase();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/database/vacuum");
        expect(wrapper.vm.databaseActionMessage).toBe("Vacuum success");
    });

    it("displays Free Space from database health", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") return Promise.resolve({ data: { app_info: { version: "1.0.0" } } });
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: {} } });
            if (url === "/api/v1/database/health")
                return Promise.resolve({
                    data: {
                        database: {
                            quick_check: "ok",
                            journal_mode: "wal",
                            page_size: 4096,
                            page_count: 100,
                            freelist_pages: 0,
                            estimated_free_bytes: 1073741824,
                        },
                    },
                });
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: [] });
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        wrapper.vm.showAdvanced = true;
        await vi.runOnlyPendingTimers();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Free Space");
        expect(wrapper.text()).toContain("1 GB");
    });

    it("displays 0 Bytes when database health has no estimated_free_bytes", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") return Promise.resolve({ data: { app_info: { version: "1.0.0" } } });
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: {} } });
            if (url === "/api/v1/database/health")
                return Promise.resolve({
                    data: { database: { quick_check: "ok", journal_mode: "wal" } },
                });
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: [] });
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        wrapper.vm.showAdvanced = true;
        await vi.runOnlyPendingTimers();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Free Space");
        expect(wrapper.text()).toContain("0 Bytes");
    });

    it("shows unknown fallbacks for missing environment paths", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info")
                return Promise.resolve({
                    data: {
                        app_info: {
                            version: "1.0.0",
                            python_version: "3.11.0",
                            lxmf_version: "0.2.0",
                            rns_version: "0.1.0",
                            reticulum_config_path: null,
                            database_path: null,
                        },
                    },
                });
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: {} } });
            if (url === "/api/v1/database/health") return Promise.resolve({ data: { database: {} } });
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: [] });
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        await vi.runOnlyPendingTimers();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Reticulum Config");
        expect(wrapper.text()).toContain("Database Path");
        expect(wrapper.text()).toContain("unknown");
    });
});
