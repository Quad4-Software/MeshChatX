// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import RNProbePage from "@/features/rnprobe/RNProbePage.svelte";
import DialogUtils from "@/js/DialogUtils";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    isValidProbeDestinationHash,
    isValidProbeFullName,
    parseProbeSummary,
    isProbeDelivered,
    isProbeTimeout,
} from "@/features/rnprobe/lib/probeFormat.ts";
import { registerRnprobeFeature } from "@/features/rnprobe/index.ts";
import { clearRoutes, listRoutes } from "@/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "@/js/registries/featureRegistry.js";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
    },
}));

describe("rnprobe lib helpers", () => {
    it("validates destination hash and full name", () => {
        expect(isValidProbeDestinationHash("a".repeat(32))).toBe(true);
        expect(isValidProbeDestinationHash("invalid-hash")).toBe(false);
        expect(isValidProbeFullName("lxmf.delivery")).toBe(true);
        expect(isValidProbeFullName("")).toBe(false);
        expect(isValidProbeFullName(null)).toBe(false);
    });

    it("parses probe summary safely", () => {
        const summary = parseProbeSummary({
            sent: 3,
            delivered: 2,
            timeouts: 1,
            failed: 0,
        });
        expect(summary.sent).toBe(3);
        expect(summary.delivered).toBe(2);
        expect(summary.timeouts).toBe(1);
        expect(summary.failed).toBe(0);
    });

    it("classifies probe result status", () => {
        expect(isProbeDelivered({ probe_number: 1, size: 16, destination: "dest", status: "delivered" })).toBe(true);
        expect(isProbeDelivered({ probe_number: 1, size: 16, destination: "dest", status: "timeout" })).toBe(false);
        expect(isProbeTimeout({ probe_number: 1, size: 16, destination: "dest", status: "timeout" })).toBe(true);
    });
});

describe("registerRnprobeFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers rnprobe route correctly", () => {
        registerRnprobeFeature();
        expect(listFeatureIds()).toContain("rnprobe");
        const route = listRoutes().find((r) => r.name === "rnprobe");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/rnprobe");
        expect(route?.mount).toBe("svelte");
    });
});

describe("RNProbePage.svelte", () => {
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
            app: { tools: "Tools" },
            tools: {
                back_to_tools: "Back",
                rnprobe: { description: "tools.rnprobe.description" },
            },
            rnprobe: {
                title: "RNProbe",
                network_diagnostics: "Network Diagnostics",
                destination_hash: "Destination Hash",
                full_destination_name: "Full Name",
                probe_size_bytes: "Size",
                number_of_probes: "Count",
                wait_between_probes: "Wait",
                start_probe: "Start",
                stop: "Stop",
                clear_results: "Clear",
                summary: "Summary",
                sent: "Sent",
                delivered: "Delivered",
                timeouts: "Timeouts",
                failed: "Failed",
                probe_results: "Results",
                probe_responses_realtime: "Realtime",
                no_probes_yet: "No probes yet",
                probe_number: "Probe #{number}",
                bytes: "bytes",
                hops: "Hops",
                rtt: "RTT",
                rssi: "RSSI",
                snr: "SNR",
                quality: "Quality",
                timeout: "Timeout",
                invalid_hash: "Invalid Hash",
                provide_full_name: "Provide Name",
                failed_to_probe: "Failed to probe",
            },
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("renders the rnprobe page", () => {
        render(RNProbePage);
        expect(screen.getByText("RNProbe")).toBeTruthy();
    });

    it("alerts on invalid hash", async () => {
        render(RNProbePage);
        await fireEvent.click(screen.getByText("Start"));
        expect(DialogUtils.alert).toHaveBeenCalledWith("Invalid Hash");
    });

    it("runs probe and displays results", async () => {
        axiosMock.post.mockResolvedValue({
            data: {
                sent: 1,
                delivered: 1,
                timeouts: 0,
                failed: 0,
                results: [
                    {
                        probe_number: 1,
                        size: 16,
                        destination: "7b746057a7294469799cd8d7d429676a",
                        status: "delivered",
                        hops: 2,
                        rtt_string: "45.67ms",
                        reception_stats: { rssi: -65, snr: 8, quality: 95 },
                    },
                ],
            },
        });

        render(RNProbePage);
        const hashInput = screen.getByPlaceholderText(/7b746057/);
        await fireEvent.input(hashInput, { target: { value: "a".repeat(32) } });

        await fireEvent.click(screen.getByText("Start"));

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalled();
        });

        expect(screen.getByText(/45.67ms/)).toBeTruthy();
        expect(screen.getByText(/RSSI: -65 dBm/)).toBeTruthy();
    });
});
