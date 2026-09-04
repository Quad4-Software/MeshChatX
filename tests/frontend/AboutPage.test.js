import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AboutPage from "@/components/about/AboutPage.vue";
import ElectronUtils from "@/js/ElectronUtils";
import DialogUtils from "@/js/DialogUtils";
import ToastUtils from "@/js/ToastUtils";
import { dispatchWsEvent } from "@/js/registries/wsEventRegistry.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

describe("AboutPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        localStorage.clear();
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
            lxst_version: "0.3.0",
            python_version: "3.11.0",
            reticulum_config_path: "/path/to/config",
            database_path: "/path/to/db",
            database_file_size: 1024,
            integrity_issues: [],
            landlock_requested: true,
            landlock_active: true,
            landlock_auto_enabled: true,
            appcontainer_requested: false,
            appcontainer_active: false,
            appcontainer_supported: false,
            seccomp_requested: true,
            seccomp_active: false,
            seccomp_kernel_supported: true,
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
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/app/sessions");

        expect(wrapper.text()).toContain("about.app_name");
        expect(wrapper.text()).toContain("about.tagline_link");
        expect(wrapper.text()).toContain("about.environment_information");
        expect(wrapper.text()).toContain("/path/to/config");
        expect(wrapper.text()).toContain("/path/to/db");

        expect(wrapper.text()).toContain("about.dependency_chain");
        expect(wrapper.text()).toContain("LXMFy");
        expect(wrapper.text()).toContain("LXMF");
        expect(wrapper.text()).toContain("LXST");
        expect(wrapper.text()).toContain("0.3.0");
        expect(wrapper.text()).toContain("RNS");

        expect(wrapper.text()).toContain("about.sandbox_title");
        expect(wrapper.text()).toContain("about.integrity_monitoring_title");
        expect(wrapper.text()).toContain("app.landlock_status");
        expect(wrapper.text()).toContain("app.enabled");
        expect(wrapper.text()).toContain("app.seccomp_status");
        expect(wrapper.text()).toContain("about.sandbox_type_landlock");

        expect(wrapper.text()).toContain("about.backend_stack");
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
        expect(wrapper.text()).toContain("about.environment_information");
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

    it("restartRns posts reticulum reload endpoint", async () => {
        const wrapper = mountAboutPage();
        wrapper.vm.appInfo = { version: "1.0.0" };
        await wrapper.vm.$nextTick();

        axiosMock.post.mockResolvedValueOnce({ data: { message: "RNS restarted" } });
        await wrapper.vm.restartRns();

        expect(ToastUtils.loading).toHaveBeenCalledWith("app.reloading_rns", 0, "about-rns-reload");
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
        expect(ToastUtils.dismiss).toHaveBeenCalledWith("about-rns-reload");
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

        expect(axiosMock.get).toHaveBeenCalledTimes(5); // info, sessions, health, snapshots, backups

        vi.advanceTimersByTime(5000);
        expect(axiosMock.get).toHaveBeenCalledTimes(7); // +info +sessions from updateInterval

        vi.advanceTimersByTime(5000);
        expect(axiosMock.get).toHaveBeenCalledTimes(9); // +info +sessions again
    });

    it("handles vacuum database action and shows success toast", async () => {
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

        await wrapper.vm.vacuumDatabase();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/database/vacuum");
        expect(wrapper.vm.databaseActionMessage).toBe("Vacuum success");
        expect(ToastUtils.success).toHaveBeenCalledWith("about.vacuum_complete");
    });

    it("shows error toast when vacuum fails", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                app_info: {},
                config: {},
                database: {},
            },
        });
        const apiErr = new Error("vacuum failed");
        apiErr.response = { data: { message: "Failed to vacuum database: locked" } };
        axiosMock.post.mockRejectedValue(apiErr);

        const wrapper = mountAboutPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.vacuumDatabase();

        expect(ToastUtils.error).toHaveBeenCalledWith("Failed to vacuum database: locked");
        expect(wrapper.vm.databaseActionError).toBe("about.vacuum_failed");
    });

    it("handles database recovery and shows success toast", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        axiosMock.get.mockResolvedValue({
            data: {
                app_info: {},
                config: {},
                database: {
                    quick_check: "ok",
                    journal_mode: "wal",
                    page_count: 1,
                    estimated_free_bytes: 0,
                },
            },
        });
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/database/recover") {
                return Promise.resolve({
                    data: {
                        message: "Database recovery routine completed",
                        database: {
                            health: {
                                quick_check: "ok",
                                journal_mode: "wal",
                                page_count: 2,
                                estimated_free_bytes: 100,
                            },
                            actions: [{ step: "wal_checkpoint", result: [] }],
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountAboutPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.runRecovery();

        expect(DialogUtils.confirm).toHaveBeenCalledWith("about.recovery_confirm");
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/database/recover");
        expect(ToastUtils.success).toHaveBeenCalledWith("about.recovery_complete");
        expect(wrapper.vm.databaseRecoveryActions.length).toBe(1);
    });

    it("does not run recovery when user cancels the confirm dialog", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(false);
        axiosMock.get.mockResolvedValue({
            data: { app_info: {}, config: {}, database: {} },
        });

        const wrapper = mountAboutPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.runRecovery();

        expect(DialogUtils.confirm).toHaveBeenCalledWith("about.recovery_confirm");
        expect(axiosMock.post).not.toHaveBeenCalledWith("/api/v1/database/recover");
        expect(ToastUtils.success).not.toHaveBeenCalledWith("about.recovery_complete");
    });

    it("shows error toast when recovery fails", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        axiosMock.get.mockResolvedValue({
            data: { app_info: {}, config: {}, database: {} },
        });
        const apiErr = new Error("recover failed");
        apiErr.response = { data: { message: "Failed to recover database: corrupt" } };
        axiosMock.post.mockRejectedValue(apiErr);

        const wrapper = mountAboutPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.runRecovery();

        expect(ToastUtils.error).toHaveBeenCalledWith("Failed to recover database: corrupt");
        expect(wrapper.vm.databaseActionError).toBe("about.recovery_failed");
    });

    it("runs auto recover and schedules relaunch when a compatible backup is restored", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        axiosMock.get.mockResolvedValue({
            data: { app_info: {}, config: {}, database: {} },
        });
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/database/auto-recover") {
                return Promise.resolve({
                    data: {
                        strategy: "restore_backup",
                        message: "Restored database from backup-1.zip",
                        requires_relaunch: true,
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountAboutPage();
        await wrapper.vm.$nextTick();
        const scheduleSpy = vi.spyOn(wrapper.vm, "scheduleRestoreRelaunch");

        await wrapper.vm.runAutoRecover();

        expect(DialogUtils.confirm).toHaveBeenCalledWith("about.auto_recover_confirm");
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/database/auto-recover", { relaunch: true });
        expect(ToastUtils.success).toHaveBeenCalledWith("Restored database from backup-1.zip");
        expect(scheduleSpy).toHaveBeenCalled();
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

        expect(wrapper.text()).toContain("about.free_space");
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

        expect(wrapper.text()).toContain("about.free_space");
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

        expect(wrapper.text()).toContain("about.reticulum_config");
        expect(wrapper.text()).toContain("about.database_path");
        expect(wrapper.text()).toContain("about.path_unknown");
    });

    it("shows MeshChatX usage insights from app info", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") {
                return Promise.resolve({
                    data: {
                        app_info: {
                            version: "1.0.0",
                            host_platform: "linux",
                            memory_usage: {
                                rss: 128 * 1024 * 1024,
                                vms: 256 * 1024 * 1024,
                                cpu_percent: 2.5,
                                num_threads: 18,
                                create_time: Date.now() / 1000 - 125,
                            },
                            battery_usage: {
                                avg_cpu_percent: 4.0,
                                machine_share_percent: 1.0,
                                estimated_percent_per_hour: 0.4,
                                intensity: "low",
                                confidence: "estimate",
                                method: "cpu_time",
                            },
                            resource_breakdown: [
                                { name: "backend", rss: 128 * 1024 * 1024, cpu_percent: 2.5 },
                                { name: "child:bot", rss: 64 * 1024 * 1024, cpu_percent: 12.0 },
                            ],
                            reticulum_stats: {
                                memory_cleanup: { path_table_size: 42, sqlite_relaxed: false },
                            },
                        },
                    },
                });
            }
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: {} } });
            if (url === "/api/v1/database/health") return Promise.resolve({ data: { database: {} } });
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: [] });
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        await vi.runOnlyPendingTimers();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getAppInfo();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("about.usage_insights");
        expect(wrapper.text()).toContain("about.app_battery_use");
        expect(wrapper.text()).toContain("about.battery_saver");
        expect(wrapper.text()).toContain("about.battery_saver_off");
        expect(wrapper.text()).toContain("about.top_memory_consumer");
        expect(wrapper.text()).toContain("about.top_cpu_consumer");
        expect(wrapper.vm.topMemoryConsumerLabel).toContain("backend");
        expect(wrapper.vm.topCpuConsumerLabel).toContain("child:bot");
        expect(wrapper.vm.batteryUsageLabel).toContain("0.4%/hr");
        expect(wrapper.text()).toContain("about.memory_rss");
        expect(wrapper.text()).toContain("about.process_cpu");
        expect(wrapper.vm.processUptimeLabel).toMatch(/2m/);
        expect(wrapper.vm.showHostBattery).toBe(false);
        expect(wrapper.text()).not.toContain("about.env_battery");
    });

    it("shows battery saver active measures when enabled", async () => {
        const { saveBatterySaverPrefs } = await import("../../meshchatx/src/frontend/js/settings/batterySaverPrefs.js");
        saveBatterySaverPrefs({ enabled: true });

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") {
                return Promise.resolve({
                    data: {
                        app_info: {
                            version: "1.0.0",
                            host_platform: "linux",
                            memory_usage: { rss: 1, vms: 1 },
                        },
                    },
                });
            }
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: {} } });
            if (url === "/api/v1/database/health") return Promise.resolve({ data: { database: {} } });
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: [] });
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        await vi.runOnlyPendingTimers();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getAppInfo();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("about.battery_saver_on");
        expect(wrapper.text()).toContain("about.battery_saver_measures");
        expect(wrapper.vm.batterySaverActiveMeasures.length).toBeGreaterThan(0);
    });

    it("loads active sessions with IP and user agent and applies websocket updates", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") {
                return Promise.resolve({ data: { app_info: { version: "1.0.0" } } });
            }
            if (url === "/api/v1/config") {
                return Promise.resolve({ data: { config: {} } });
            }
            if (url === "/api/v1/app/sessions") {
                return Promise.resolve({
                    data: {
                        count: 2,
                        sessions: [
                            {
                                id: "sess-a",
                                ip: "127.0.0.1",
                                user_agent: "Browser/A",
                                connected_at: 1700000000,
                            },
                            {
                                id: "sess-b",
                                ip: "10.0.0.2",
                                user_agent: "Browser/B",
                                connected_at: 1700000001,
                            },
                        ],
                        warning: true,
                        warning_enabled: true,
                    },
                });
            }
            if (url === "/api/v1/database/health") {
                return Promise.resolve({ data: { database: {} } });
            }
            if (url === "/api/v1/database/snapshots") {
                return Promise.resolve({ data: { snapshots: [], total: 0 } });
            }
            if (url === "/api/v1/database/backups") {
                return Promise.resolve({ data: { backups: [], total: 0 } });
            }
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        await vi.runOnlyPendingTimers();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/app/sessions");
        expect(wrapper.text()).toContain("about.active_sessions");
        expect(wrapper.text()).toContain("127.0.0.1");
        expect(wrapper.text()).toContain("10.0.0.2");
        expect(wrapper.text()).toContain("Browser/A");
        expect(wrapper.text()).toContain("Browser/B");
        expect(wrapper.vm.activeSessionCount).toBe(2);

        await dispatchWsEvent("app.sessions.updated", {
            count: 1,
            sessions: [
                {
                    id: "sess-a",
                    ip: "127.0.0.1",
                    user_agent: "Browser/A",
                    connected_at: 1700000000,
                },
            ],
            warning: false,
            warning_enabled: true,
        });
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.activeSessionCount).toBe(1);
        expect(wrapper.text()).toContain("Browser/A");
        expect(wrapper.text()).not.toContain("Browser/B");
        expect(wrapper.text()).not.toContain("10.0.0.2");
    });
});
