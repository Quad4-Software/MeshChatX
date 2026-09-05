// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AboutPage from "@/features/about/AboutPage.svelte";
import ElectronUtils from "@/js/ElectronUtils";
import DialogUtils from "@/js/DialogUtils";
import ToastUtils from "@/js/ToastUtils";
import { dispatchWsEvent } from "@/js/registries/wsEventRegistry.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";
import { saveBatterySaverPrefs } from "@/js/settings/batterySaverPrefs.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
        alert: vi.fn(),
    },
}));

describe("AboutPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        registerTranslator(null);
        registerFallbackMessages(en);

        axiosMock = {
            get: vi.fn().mockImplementation(() => Promise.resolve({ data: {} })),
            post: vi.fn().mockImplementation(() => Promise.resolve({ data: {} })),
            delete: vi.fn().mockImplementation(() => Promise.resolve({ data: {} })),
        };
        window.api = axiosMock;
        window.URL.createObjectURL = vi.fn();
        window.URL.revokeObjectURL = vi.fn();

        window.electron = {
            getMemoryUsage: vi.fn().mockResolvedValue(null),
            electronVersion: vi.fn().mockReturnValue("1.0.0"),
            chromeVersion: vi.fn().mockReturnValue("1.0.0"),
            nodeVersion: vi.fn().mockReturnValue("1.0.0"),
            appVersion: vi.fn().mockResolvedValue("1.0.0"),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        delete window.electron;
    });

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

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") return Promise.resolve({ data: { app_info: appInfo } });
            if (url === "/api/v1/app/sessions") return Promise.resolve({ data: { count: 0, sessions: [] } });
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
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: { snapshots: [], total: 0 } });
            if (url === "/api/v1/database/backups") return Promise.resolve({ data: { backups: [], total: 0 } });
            return Promise.reject(new Error("Not found"));
        });

        render(AboutPage);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/app/info");
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/app/sessions");
        });

        expect(screen.getAllByText("MeshChatX").length).toBeGreaterThan(0);
        expect(screen.getByText("Reticulum Network Stack")).toBeTruthy();
        expect(screen.getByText("Environment Information")).toBeTruthy();
        expect(screen.getByText("/path/to/config")).toBeTruthy();
        expect(screen.getByText("/path/to/db")).toBeTruthy();
        expect(screen.getByText("Stack versions")).toBeTruthy();
        expect(screen.getByText("LXMFy")).toBeTruthy();
        expect(screen.getByText("LXMF")).toBeTruthy();
        expect(screen.getByText("LXST")).toBeTruthy();
        expect(screen.getByText("RNS")).toBeTruthy();
        expect(screen.getByText("Process sandboxing")).toBeTruthy();
        expect(screen.getByText("Python packages")).toBeTruthy();
        expect(screen.getByText("aiohttp")).toBeTruthy();
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
            if (url === "/api/v1/app/sessions") return Promise.resolve({ data: { count: 0, sessions: [] } });
            if (url === "/api/v1/database/health") return Promise.resolve({ data: { database: {} } });
            if (url === "/api/v1/database/snapshots") return Promise.resolve({ data: { snapshots: [], total: 0 } });
            if (url === "/api/v1/database/backups") return Promise.resolve({ data: { backups: [], total: 0 } });
            return Promise.reject(new Error("Not found"));
        });

        render(AboutPage);

        await waitFor(() => {
            expect(getMemoryUsageSpy).toHaveBeenCalled();
        });
        expect(screen.getByText("Environment Information")).toBeTruthy();
    });

    it("handles shutdown action", async () => {
        const confirmSpy = vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        const axiosPostSpy = axiosMock.post.mockResolvedValue({ data: { message: "Shutting down..." } });
        const shutdownSpy = vi.spyOn(ElectronUtils, "shutdown").mockImplementation(() => {});
        vi.spyOn(ElectronUtils, "isElectron").mockReturnValue(true);

        render(AboutPage);

        const shutdownBtn = screen.getByText("Shutdown");
        await fireEvent.click(shutdownBtn);

        expect(confirmSpy).toHaveBeenCalled();
        expect(axiosPostSpy).toHaveBeenCalledWith("/api/v1/app/shutdown");
        expect(shutdownSpy).toHaveBeenCalled();
    });

    it("restartRns posts reticulum reload endpoint", async () => {
        axiosMock.post.mockResolvedValueOnce({ data: { message: "RNS restarted" } });

        render(AboutPage);

        const restartBtn = screen.getByText("Restart RNS");
        await fireEvent.click(restartBtn);

        expect(ToastUtils.loading).toHaveBeenCalledWith("Reloading RNS...", 0, "about-rns-reload");
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
        expect(ToastUtils.dismiss).toHaveBeenCalledWith("about-rns-reload");
    });

    it("handles vacuum database action and shows success toast", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                app_info: {},
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
        axiosMock.post.mockResolvedValue({ data: { message: "Database vacuum finished." } });

        render(AboutPage);

        const vacuumBtn = screen.getByText("Vacuum");
        await fireEvent.click(vacuumBtn);

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/database/vacuum");
        expect(ToastUtils.success).toHaveBeenCalledWith("Database vacuum finished.");
    });

    it("shows error toast when vacuum fails", async () => {
        axiosMock.get.mockResolvedValue({
            data: { app_info: {}, database: {} },
        });
        const apiErr = new Error("vacuum failed");
        apiErr.response = { data: { message: "Failed to vacuum database: locked" } };
        axiosMock.post.mockRejectedValue(apiErr);

        render(AboutPage);

        const vacuumBtn = screen.getByText("Vacuum");
        await fireEvent.click(vacuumBtn);

        expect(ToastUtils.error).toHaveBeenCalledWith("Failed to vacuum database: locked");
    });

    it("handles database recovery and shows success toast", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        axiosMock.get.mockResolvedValue({
            data: { app_info: {}, database: {} },
        });
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/database/recover") {
                return Promise.resolve({
                    data: {
                        message: "Database recovery finished.",
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

        render(AboutPage);

        const recoverBtn = screen.getByText("Recovery");
        await fireEvent.click(recoverBtn);

        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/database/recover");
        expect(ToastUtils.success).toHaveBeenCalledWith("Database recovery finished.");
    });

    it("does not run recovery when user cancels the confirm dialog", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(false);
        axiosMock.get.mockResolvedValue({
            data: { app_info: {}, database: {} },
        });

        render(AboutPage);

        const recoverBtn = screen.getByText("Recovery");
        await fireEvent.click(recoverBtn);

        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(axiosMock.post).not.toHaveBeenCalledWith("/api/v1/database/recover");
    });

    it("runs auto recover and schedules relaunch when a compatible backup is restored", async () => {
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        axiosMock.get.mockResolvedValue({
            data: { app_info: {}, database: {} },
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

        render(AboutPage);

        const autoRecoverBtn = screen.getByText("Auto Recover");
        await fireEvent.click(autoRecoverBtn);

        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/database/auto-recover", { relaunch: true });
        expect(ToastUtils.success).toHaveBeenCalledWith("Restored database from backup-1.zip");
    });

    it("displays Free Space from database health", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") return Promise.resolve({ data: { app_info: { version: "1.0.0" } } });
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
            return Promise.resolve({ data: {} });
        });

        render(AboutPage);

        await waitFor(() => {
            expect(screen.getByText(/Free space/i)).toBeTruthy();
            expect(screen.getByText("1 GB")).toBeTruthy();
        });
    });

    it("displays 0 Bytes when database health has no estimated_free_bytes", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") return Promise.resolve({ data: { app_info: { version: "1.0.0" } } });
            if (url === "/api/v1/database/health")
                return Promise.resolve({
                    data: { database: { quick_check: "ok", journal_mode: "wal" } },
                });
            return Promise.resolve({ data: {} });
        });

        render(AboutPage);

        await waitFor(() => {
            expect(screen.getByText(/Free space/i)).toBeTruthy();
            expect(screen.getAllByText("0 Bytes").length).toBeGreaterThanOrEqual(1);
        });
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
            return Promise.resolve({ data: {} });
        });

        render(AboutPage);

        await waitFor(() => {
            expect(screen.getByText(/Reticulum Config/i)).toBeTruthy();
            expect(screen.getByText(/Database Path/i)).toBeTruthy();
            expect(screen.getAllByText("unknown").length).toBeGreaterThan(0);
        });
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
            return Promise.resolve({ data: {} });
        });

        render(AboutPage);

        await waitFor(() => {
            expect(screen.getByText(/MeshChatX usage/i)).toBeTruthy();
            expect(screen.getByText(/Battery saver/i)).toBeTruthy();
            expect(screen.getByText("Off")).toBeTruthy();
            expect(screen.getByText(/Top memory/i)).toBeTruthy();
            expect(screen.getByText(/Top CPU/i)).toBeTruthy();
        });
    });

    it("shows battery saver active measures when enabled", async () => {
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
            return Promise.resolve({ data: {} });
        });

        render(AboutPage);

        await waitFor(() => {
            expect(screen.getByText("On")).toBeTruthy();
            expect(screen.getByText(/Active measures/i)).toBeTruthy();
        });
    });

    it("loads active sessions with IP and user agent and applies websocket updates", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") {
                return Promise.resolve({ data: { app_info: { version: "1.0.0" } } });
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
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        render(AboutPage);

        await waitFor(() => {
            expect(screen.getByText(/Active sessions/i)).toBeTruthy();
            expect(screen.getByText("127.0.0.1")).toBeTruthy();
            expect(screen.getByText("10.0.0.2")).toBeTruthy();
            expect(screen.getByText("Browser/A")).toBeTruthy();
            expect(screen.getByText("Browser/B")).toBeTruthy();
        });

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
        });

        await waitFor(() => {
            expect(screen.getByText("Browser/A")).toBeTruthy();
            expect(screen.queryByText("Browser/B")).toBeNull();
        });
    });
});
