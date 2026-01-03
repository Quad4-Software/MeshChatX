import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AboutPage from "@/components/about/AboutPage.vue";

describe("AboutPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        vi.useFakeTimers();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.axios = axiosMock;
        window.URL.createObjectURL = vi.fn();
        window.URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
        vi.useRealTimers();
        delete window.axios;
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
            return Promise.reject(new Error("Not found"));
        });

        const wrapper = mountAboutPage();
        await vi.runOnlyPendingTimers();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // Extra tick for multiple async calls

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/app/info");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");

        expect(wrapper.text()).toContain("Reticulum MeshChatX");
        expect(wrapper.text()).toContain("hash1");
        expect(wrapper.text()).toContain("hash2");
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

        expect(axiosMock.get).toHaveBeenCalledTimes(3); // info, config, health

        vi.advanceTimersByTime(5000);
        expect(axiosMock.get).toHaveBeenCalledTimes(4);

        vi.advanceTimersByTime(5000);
        expect(axiosMock.get).toHaveBeenCalledTimes(5);
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
});
