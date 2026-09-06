import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import PingPage from "@/features/ping/PingPage.svelte";
import ToastUtils from "@/js/ToastUtils";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import { formatPingSuccess, isValidPingDestinationHash, isValidPingTimeout } from "@/features/ping/lib/pingFormat.ts";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

describe("pingFormat", () => {
    it("validates hash and timeout", () => {
        expect(isValidPingDestinationHash("a".repeat(32))).toBe(true);
        expect(isValidPingDestinationHash("short")).toBe(false);
        expect(isValidPingTimeout(10)).toBe(true);
        expect(isValidPingTimeout(0)).toBe(false);
    });

    it("formats success lines", () => {
        const { line, summary } = formatPingSuccess(
            {
                rtt: 0.1234,
                hops_there: 1,
                hops_back: 1,
                rssi: -50,
                snr: 5,
                quality: 100,
                receiving_interface: "UDP",
            },
            1
        );
        expect(line).toContain("duration=123.400ms");
        expect(line).toContain("rssi=-50dBm");
        expect(summary.duration).toBe("123.400ms");
    });
});

describe("PingPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            isCancel: vi.fn(() => false),
        };
        window.api = axiosMock;
        registerTranslator(null);
        registerFallbackMessages({
            app: { tools: "Tools", interfaces: "via" },
            tools: {
                back_to_tools: "Back",
                ping: { description: "tools.ping.description" },
            },
            ping: {
                title: "ping.title",
                description: "ping.description {code}",
                destination_hash: "Hash",
                timeout_seconds: "Timeout",
                start_ping: "ping.start_ping",
                stop: "ping.stop",
                clear_results: "Clear",
                drop_path: "ping.drop_path",
                status: "Status",
                running: "running",
                idle: "idle",
                last_rtt: "RTT",
                last_error: "Err",
                console_output: "Out",
                streaming_responses: "stream",
                no_pings_yet: "none",
                invalid_hash: "ping.invalid_hash",
                timeout_must_be_number: "bad timeout",
            },
            rnprobe: { hops: "hops", rssi: "rssi", snr: "snr", quality: "quality" },
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("renders the ping page", () => {
        render(PingPage);
        expect(screen.getByText("ping.title")).toBeTruthy();
    });

    it("shows alert for invalid hash when starting", async () => {
        render(PingPage);
        await fireEvent.click(screen.getByText("ping.start_ping"));
        expect(ToastUtils.error).toHaveBeenCalledWith("ping.invalid_hash");
    });

    it("pings and displays results", async () => {
        axiosMock.post.mockResolvedValue({
            data: {
                ping_result: {
                    rtt: 0.1234,
                    hops_there: 1,
                    hops_back: 1,
                    rssi: -50,
                    snr: 5,
                    quality: 100,
                    receiving_interface: "UDP",
                },
            },
        });

        render(PingPage);
        const hashInput = screen.getByPlaceholderText(/7b746057/);
        await fireEvent.input(hashInput, { target: { value: "a".repeat(32) } });
        await fireEvent.click(screen.getByText("ping.start_ping"));

        await waitFor(() => {
            expect(screen.getByText(/duration=123.400ms/)).toBeTruthy();
        });
        expect(screen.getByText(/rssi=-50dBm/)).toBeTruthy();
        expect(screen.getByText("seq #1")).toBeTruthy();

        await fireEvent.click(screen.getByText("ping.stop"));
    });

    it("terminates previous loop when stop and start are called sequentially", async () => {
        axiosMock.post.mockResolvedValue({
            data: {
                ping_result: {
                    rtt: 0.1,
                    hops_there: 1,
                    hops_back: 1,
                    receiving_interface: "UDP",
                },
            },
        });

        render(PingPage);
        const hashInput = screen.getByPlaceholderText(/7b746057/);
        await fireEvent.input(hashInput, { target: { value: "a".repeat(32) } });

        await fireEvent.click(screen.getByText("ping.start_ping"));
        await waitFor(() => expect(axiosMock.post).toHaveBeenCalled());
        await fireEvent.click(screen.getByText("ping.stop"));
        await fireEvent.click(screen.getByText("ping.start_ping"));
        await new Promise((r) => setTimeout(r, 120));
        expect(axiosMock.post.mock.calls.length).toBeLessThanOrEqual(4);
        await fireEvent.click(screen.getByText("ping.stop"));
    });

    it("calls drop path API", async () => {
        axiosMock.post.mockResolvedValue({ data: { message: "Path dropped" } });
        render(PingPage);
        const hashInput = screen.getByPlaceholderText(/7b746057/);
        await fireEvent.input(hashInput, { target: { value: "a".repeat(32) } });

        await fireEvent.click(screen.getByText("ping.drop_path"));

        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/destination/${"a".repeat(32)}/drop-path`);
        expect(ToastUtils.success).toHaveBeenCalledWith("Path dropped");
    });
});
