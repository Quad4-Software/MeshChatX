// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import RNPathTracePage from "@/features/rnpath-trace/RNPathTracePage.svelte";
import ToastUtils from "@/js/ToastUtils";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    isValidTraceHash,
    formatTraceHash,
    getNodeClass,
    getNodeIcon,
    isUnknownTraceNode,
} from "@/features/rnpath-trace/lib/traceFormat.ts";
import { registerRnpathTraceFeature } from "@/features/rnpath-trace/index.ts";
import { clearRoutes, listRoutes } from "@/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "@/js/registries/featureRegistry.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe("rnpath-trace lib helpers", () => {
    it("validates destination hash", () => {
        expect(isValidTraceHash("a".repeat(32))).toBe(true);
        expect(isValidTraceHash("invalid")).toBe(false);
    });

    it("formats hash with ellipsis", () => {
        expect(formatTraceHash("0123456789abcdef0123456789abcdef")).toBe("01234567...");
        expect(formatTraceHash("")).toBe("");
        expect(formatTraceHash(null)).toBe("");
    });

    it("returns node class and icon for different node types", () => {
        expect(getNodeClass({ type: "local" })).toContain("bg-blue-600");
        expect(getNodeClass({ type: "destination" })).toContain("bg-emerald-600");
        expect(getNodeClass({ type: "unknown" })).toContain("border-dashed");
        expect(getNodeClass({ type: "hop" })).toContain("bg-indigo-600");

        expect(getNodeIcon({ type: "local" })).toBe("home");
        expect(getNodeIcon({ type: "destination" })).toBe("flag-variant");
        expect(getNodeIcon({ type: "unknown" })).toBe("dots-horizontal");
        expect(getNodeIcon({ type: "hop" })).toBe("router-wireless");

        expect(isUnknownTraceNode({ type: "unknown" })).toBe(true);
        expect(isUnknownTraceNode({ type: "local" })).toBe(false);
    });
});

describe("registerRnpathTraceFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers rnpath-trace route correctly", () => {
        registerRnpathTraceFeature();
        expect(listFeatureIds()).toContain("rnpath-trace");
        const route = listRoutes().find((r) => r.name === "rnpath-trace");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/rnpath-trace");
        expect(route?.mount).toBe("svelte");
    });
});

describe("RNPathTracePage.svelte", () => {
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
            common: {
                copy_to_clipboard: "Copy",
                copied: "Copied",
            },
            tools: {
                back_to_tools: "Back",
                rnpath_trace: {
                    title: "Path Trace",
                    description: "Trace path to destination",
                    trace: "Trace",
                    tracing: "Tracing...",
                    total_hops: "Total Hops",
                    interface: "Interface",
                    next_hop: "Next Hop",
                    unknown_hops: "{count} Unknown Hops",
                    ping_test: "Ping Test",
                },
            },
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("renders the path trace page", () => {
        render(RNPathTracePage);
        expect(screen.getByText("Path Trace")).toBeTruthy();
    });

    it("executes trace and renders result nodes", async () => {
        const hash = "a".repeat(32);
        axiosMock.get.mockResolvedValue({
            data: {
                destination: hash,
                hops: 2,
                interface: "AutoInterface[Default]",
                next_hop: "b".repeat(32),
                path: [
                    { type: "local", hash: "c".repeat(32), name: "Local Node" },
                    { type: "hop", hash: "b".repeat(32), name: "Next Hop", interface: "AutoInterface[Default]" },
                    { type: "destination", hash, hops: 2 },
                ],
            },
        });

        render(RNPathTracePage);
        const input = screen.getByPlaceholderText("input destination hash");
        await fireEvent.input(input, { target: { value: hash } });

        const traceBtn = screen.getByTitle("Trace");
        await fireEvent.click(traceBtn);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(`/api/v1/rnpath/trace/${hash}`);
        });

        expect(screen.getAllByText("Local Node").length).toBeGreaterThan(0);
        expect(screen.getAllByText("Next Hop").length).toBeGreaterThan(0);
        expect(screen.getAllByText("AutoInterface[Default]").length).toBeGreaterThan(0);
    });

    it("handles trace error response", async () => {
        const hash = "a".repeat(32);
        axiosMock.get.mockResolvedValue({
            data: {
                error: "Path not found after timeout",
            },
        });

        render(RNPathTracePage);
        const input = screen.getByPlaceholderText("input destination hash");
        await fireEvent.input(input, { target: { value: hash } });

        const traceBtn = screen.getByTitle("Trace");
        await fireEvent.click(traceBtn);

        await waitFor(() => {
            expect(screen.getByText("Trace Error")).toBeTruthy();
            expect(screen.getByText("Path not found after timeout")).toBeTruthy();
        });
    });
});
