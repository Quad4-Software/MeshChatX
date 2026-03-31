import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import DebugLogsPage from "@/components/debug/DebugLogsPage.vue";

// Mock axios
window.api = {
    get: vi.fn(),
};

describe("DebugLogsPage.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("fetches and displays logs", async () => {
        const mockLogs = [
            { timestamp: Date.now() / 1000, level: "INFO", module: "test", message: "Hello", is_anomaly: 0 },
            {
                timestamp: (Date.now() - 1000) / 1000,
                level: "ERROR",
                module: "test",
                message: "Boom",
                is_anomaly: 1,
                anomaly_type: "repeat",
            },
        ];

        window.api.get.mockResolvedValue({
            data: {
                logs: mockLogs,
                total: 2,
                limit: 100,
                offset: 0,
            },
        });

        const wrapper = mount(DebugLogsPage, {
            global: {
                stubs: ["MaterialDesignIcon"],
                mocks: { $t: (key) => key },
            },
        });

        await new Promise((resolve) => setTimeout(resolve, 10));
        await wrapper.vm.$nextTick();

        const container = wrapper.find(".flex-1.overflow-auto.p-4.font-mono");
        const logRows = container.findAll(".border-b");
        expect(logRows.length).toBe(2);
        expect(wrapper.text()).toContain("Hello");
        expect(wrapper.text()).toContain("Boom");
        expect(wrapper.text().toLowerCase()).toContain("repeat"); // Anomaly badge
    });

    it("handles search input", async () => {
        window.api.get.mockResolvedValue({
            data: { logs: [], total: 0, limit: 100, offset: 0 },
        });

        const wrapper = mount(DebugLogsPage, {
            global: {
                stubs: ["MaterialDesignIcon"],
                mocks: { $t: (key) => key },
            },
        });

        const searchInput = wrapper.find("input[placeholder='debug.search_logs_placeholder']");
        await searchInput.setValue("error");

        // Wait for debounce (500ms)
        await new Promise((resolve) => setTimeout(resolve, 600));

        expect(window.api.get).toHaveBeenCalledWith(
            expect.stringContaining("/api/v1/debug/logs"),
            expect.objectContaining({
                params: expect.objectContaining({ search: "error" }),
            })
        );
    });

    it("handles pagination", async () => {
        window.api.get.mockResolvedValue({
            data: {
                logs: [],
                total: 250,
                limit: 100,
                offset: 0,
            },
        });

        const wrapper = mount(DebugLogsPage, {
            global: {
                stubs: ["MaterialDesignIcon"],
                mocks: { $t: (key) => key },
            },
        });

        await new Promise((resolve) => setTimeout(resolve, 10));

        const nextButton = wrapper.findAll("button").find((b) => b.text().includes("Next"));
        await nextButton.trigger("click");

        expect(window.api.get).toHaveBeenCalledWith(
            expect.stringContaining("/api/v1/debug/logs"),
            expect.objectContaining({
                params: expect.objectContaining({ offset: 100 }),
            })
        );
    });

    it("loads access attempts when switching to Access attempts tab", async () => {
        window.api.get.mockImplementation((url) => {
            if (url.includes("access-attempts")) {
                return Promise.resolve({
                    data: {
                        attempts: [
                            {
                                id: 1,
                                created_at: Date.now() / 1000,
                                identity_hash: "ab",
                                client_ip: "10.0.0.1",
                                user_agent: "TestUA/1",
                                path: "/api/v1/auth/login",
                                method: "POST",
                                outcome: "failed_password",
                                detail: "",
                            },
                        ],
                        total: 1,
                        limit: 100,
                        offset: 0,
                    },
                });
            }
            return Promise.resolve({
                data: { logs: [], total: 0, limit: 100, offset: 0 },
            });
        });

        const wrapper = mount(DebugLogsPage, {
            global: {
                stubs: ["MaterialDesignIcon"],
                mocks: { $t: (key) => key },
            },
        });

        await new Promise((resolve) => setTimeout(resolve, 10));
        await wrapper.vm.$nextTick();

        const accessTab = wrapper.findAll("button").find((b) => b.text().includes("debug.tab_access_attempts"));
        expect(accessTab).toBeTruthy();
        await accessTab.trigger("click");
        await new Promise((resolve) => setTimeout(resolve, 10));
        await wrapper.vm.$nextTick();

        expect(window.api.get).toHaveBeenCalledWith(
            expect.stringContaining("/api/v1/debug/access-attempts"),
            expect.any(Object)
        );
        expect(wrapper.text()).toContain("failed_password");
        expect(wrapper.text()).toContain("10.0.0.1");
    });
});
