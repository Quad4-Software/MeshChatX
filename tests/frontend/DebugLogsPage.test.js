import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import DebugLogsPage from "@/components/debug/DebugLogsPage.vue";

// Mock axios
window.axios = {
    get: vi.fn(),
};

describe("DebugLogsPage.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("fetches and displays logs", async () => {
        const mockLogs = [
            { timestamp: Date.now() / 1000, level: "INFO", module: "test", message: "Hello", is_anomaly: 0 },
            { timestamp: (Date.now() - 1000) / 1000, level: "ERROR", module: "test", message: "Boom", is_anomaly: 1, anomaly_type: "repeat" },
        ];

        window.axios.get.mockResolvedValue({
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
            },
        });

        // Wait for axios
        await new Promise((resolve) => setTimeout(resolve, 10));
        await wrapper.vm.$nextTick();

        const logRows = wrapper.findAll(".border-b");
        expect(logRows.length).toBe(2);
        expect(wrapper.text()).toContain("Hello");
        expect(wrapper.text()).toContain("Boom");
        expect(wrapper.text().toLowerCase()).toContain("repeat"); // Anomaly badge
    });

    it("handles search input", async () => {
        const wrapper = mount(DebugLogsPage, {
            global: {
                stubs: ["MaterialDesignIcon"],
            },
        });

        const searchInput = wrapper.find("input[placeholder='Search logs...']");
        await searchInput.setValue("error");
        
        // Wait for debounce (500ms)
        await new Promise((resolve) => setTimeout(resolve, 600));

        expect(window.axios.get).toHaveBeenCalledWith(
            expect.stringContaining("/api/v1/debug/logs"),
            expect.objectContaining({
                params: expect.objectContaining({ search: "error" }),
            })
        );
    });

    it("handles pagination", async () => {
        window.axios.get.mockResolvedValue({
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
            },
        });

        await new Promise((resolve) => setTimeout(resolve, 10));
        
        // Click next
        const nextButton = wrapper.findAll("button").find(b => b.text().includes("Next"));
        await nextButton.trigger("click");

        expect(window.axios.get).toHaveBeenCalledWith(
            expect.stringContaining("/api/v1/debug/logs"),
            expect.objectContaining({
                params: expect.objectContaining({ offset: 100 }),
            })
        );
    });
});

