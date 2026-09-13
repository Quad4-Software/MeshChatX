import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import DebugLogsPage from "@/features/debug-logs/DebugLogsPage.svelte";
import { formatLogLine, debugLevelClass } from "@/features/debug-logs/lib/debugFormat.ts";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

window.api = {
    get: vi.fn(),
};

describe("debugFormat", () => {
    it("formats log lines and level classes", () => {
        expect(debugLevelClass("ERROR")).toContain("red");
        expect(formatLogLine({ timestamp: 1, level: "INFO", module: "m", message: "hi", is_anomaly: 0 })).toContain(
            "[INFO]"
        );
    });
});

describe("DebugLogsPage.svelte", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        Object.assign(navigator, {
            clipboard: {
                writeText: vi.fn().mockResolvedValue(undefined),
            },
        });
        registerTranslator(null);
        registerFallbackMessages({
            app: { tools: "Tools" },
            tools: { back_to_tools: "Back" },
            common: { search: "Search", all: "All", refresh: "Refresh", next: "Next", previous: "Previous" },
            debug: {
                logs_title: "Logs",
                logs_description: "desc",
                copy_logs: "Copy",
                copy_access: "Copy access",
                tab_logs: "debug.tab_logs",
                tab_access_attempts: "debug.tab_access_attempts",
                search_logs_placeholder: "debug.search_logs_placeholder",
                search_access_placeholder: "debug.search_access_placeholder",
                level: "Level",
                anomalies_only: "Anomalies",
                outcome: "Outcome",
                no_logs_found: "none",
                no_access_attempts: "none access",
                logs_copied: "copied",
                failed_copy_logs: "fail copy",
                access_copied: "access copied",
                failed_copy_access: "fail access copy",
                failed_fetch_logs: "fail logs",
                failed_fetch_access: "fail access",
            },
        });
    });

    afterEach(() => {
        cleanup();
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

        render(DebugLogsPage);

        await waitFor(() => {
            expect(screen.getByText("Hello")).toBeTruthy();
        });
        expect(screen.getByText("Boom")).toBeTruthy();
        expect(screen.getByText(/repeat/i)).toBeTruthy();
    });

    it("handles search input", async () => {
        window.api.get.mockResolvedValue({
            data: { logs: [], total: 0, limit: 100, offset: 0 },
        });

        render(DebugLogsPage);
        await waitFor(() => expect(window.api.get).toHaveBeenCalled());

        const searchInput = screen.getByPlaceholderText("debug.search_logs_placeholder");
        await fireEvent.input(searchInput, { target: { value: "error" } });

        await waitFor(
            () => {
                expect(window.api.get).toHaveBeenCalledWith(
                    expect.stringContaining("/api/v1/debug/logs"),
                    expect.objectContaining({
                        params: expect.objectContaining({ search: "error" }),
                    })
                );
            },
            { timeout: 1000 }
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

        render(DebugLogsPage);
        await waitFor(() => expect(window.api.get).toHaveBeenCalled());

        const nextButtons = screen.getAllByText("Next");
        await fireEvent.click(nextButtons[0]);

        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith(
                expect.stringContaining("/api/v1/debug/logs"),
                expect.objectContaining({
                    params: expect.objectContaining({ offset: 100 }),
                })
            );
        });
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

        render(DebugLogsPage);
        await waitFor(() => expect(window.api.get).toHaveBeenCalled());

        await fireEvent.click(screen.getByText("debug.tab_access_attempts"));

        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith(
                expect.stringContaining("/api/v1/debug/access-attempts"),
                expect.any(Object)
            );
        });
        expect(screen.getAllByText("failed_password").length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText("10.0.0.1")).toBeTruthy();
    });

    it("copies a single log line when tapping an entry", async () => {
        const mockLogs = [
            { timestamp: Date.now() / 1000, level: "ERROR", module: "web_protocol", message: "Boom", is_anomaly: 0 },
        ];

        window.api.get.mockResolvedValue({
            data: {
                logs: mockLogs,
                total: 1,
                limit: 100,
                offset: 0,
            },
        });

        render(DebugLogsPage);
        const boom = await screen.findByText("Boom");
        await fireEvent.click(boom.closest("[role='button']") || boom);

        await waitFor(() => {
            expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1);
        });
        expect(navigator.clipboard.writeText.mock.calls[0][0]).toContain("[ERROR]");
        expect(navigator.clipboard.writeText.mock.calls[0][0]).toContain("Boom");
        expect(ToastUtils.success).toHaveBeenCalled();
    });
});
