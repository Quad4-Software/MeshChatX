// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import RNPathPage from "@/features/rnpath/RNPathPage.svelte";
import ToastUtils from "@/js/ToastUtils.js";
import DialogUtils from "@/js/DialogUtils.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    buildPathQueryParams,
    buildRemoteQueryParams,
    calculateRate,
    extractInterfaceNames,
    formatDate,
    getStateColor,
    getStateText,
    isValidDestinationHash,
    parseHops,
    shortHash,
} from "@/features/rnpath/lib/pathQuery.ts";
import { registerRnpathFeature } from "@/features/rnpath/index.ts";
import { clearRoutes, listRoutes } from "@/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "@/js/registries/featureRegistry.js";

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
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(),
    },
}));

describe("rnpath lib helpers", () => {
    it("builds remote query params", () => {
        expect(buildRemoteQueryParams("")).toEqual({});
        expect(buildRemoteQueryParams("a".repeat(32), "/path/key", 20)).toEqual({
            remote: "a".repeat(32),
            identity_path: "/path/key",
            timeout: 20,
        });
    });

    it("parses hops and builds path query params", () => {
        expect(parseHops(3)).toBe(3);
        expect(parseHops("2")).toBe(2);
        expect(parseHops("")).toBeUndefined();
        expect(() => parseHops("invalid")).toThrow();

        const params = buildPathQueryParams({
            searchQuery: " test ",
            filterInterface: "UDP",
            filterHops: "1",
            currentPage: 2,
            itemsPerPage: 50,
        });
        expect(params.page).toBe(2);
        expect(params.limit).toBe(50);
        expect(params.search).toBe("test");
        expect(params.interface).toBe("UDP");
        expect(params.hops).toBe(1);
    });

    it("extracts sorted interface names", () => {
        const names = extractInterfaceNames(
            { interfaces: { UDP: {}, TCP: {} } },
            { active: [{ name: "ActiveIF" }], interfaces: [{ name: "DiscIF" }] }
        );
        expect(names).toEqual(["ActiveIF", "DiscIF", "TCP", "UDP"]);
    });

    it("calculates announce rates", () => {
        expect(calculateRate(null)).toBe("0.00");
        expect(calculateRate({ timestamps: [] })).toBe("0.00");
    });

    it("returns state color and label", () => {
        expect(getStateColor(2)).toContain("bg-green-100");
        expect(getStateColor(1)).toContain("bg-red-100");
        expect(getStateText(2)).toBe("RESPONSIVE");
        expect(getStateText(1)).toBe("UNRESPONSIVE");
        expect(getStateText(0)).toBe("UNKNOWN");
    });

    it("formats date, shortens hash, and validates hash", () => {
        expect(formatDate(0)).toBe("Unknown");
        expect(shortHash("0123456789abcdef0123456789abcdef")).toBe("01234567…");
        expect(isValidDestinationHash("a".repeat(32))).toBe(true);
        expect(isValidDestinationHash("xyz")).toBe(false);
    });
});

describe("registerRnpathFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers rnpath route correctly", () => {
        registerRnpathFeature();
        expect(listFeatureIds()).toContain("rnpath");
        const route = listRoutes().find((r) => r.name === "rnpath");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/rnpath");
        expect(route?.mount).toBe("svelte");
    });
});

describe("RNPathPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        registerTranslator(null);
        registerFallbackMessages({
            app: { tools: "Tools" },
            tools: {
                back_to_tools: "Back",
                rnpath: {
                    title: "RNPath",
                    description: "Inspect and manage Reticulum path table",
                    table: "Table",
                    rates: "Rates",
                    actions: "Actions",
                    invalid_hops: "Invalid hops count",
                    failed_fetch: "Failed to fetch path data",
                    path_requested: "Path requested for {hash}",
                    failed_request: "Failed to request path",
                    drop_confirm: "Drop path for {hash}?",
                    path_dropped: "Path dropped",
                    failed_drop: "Failed to drop path",
                    error_drop: "Error dropping path",
                    drop_via_confirm: "Drop all paths via {hash}?",
                    paths_dropped: "Paths dropped",
                    failed_drop_paths: "Failed to drop paths",
                    purge_confirm: "Purge announce queues?",
                    queues_purged: "Queues purged",
                    failed_purge: "Failed to purge queues",
                    search_placeholder: "Search paths...",
                    filter_interface: "Interface",
                    all_interfaces: "All interfaces",
                    filter_hops: "Hops",
                    all_hops: "All hops",
                    clear_filters: "Clear filters",
                    total_paths: "Total Paths",
                    responsive: "Responsive",
                    unresponsive: "Unresponsive",
                    destination: "Destination",
                    hops: "Hops",
                    next_hop: "Next Hop",
                    interface: "Interface",
                    expires: "Expires",
                    drop: "Drop",
                    request_path: "Request Path",
                    request_path_desc: "Broadcast a path request for a destination hash.",
                    request_button: "Request",
                    request_btn: "Request",
                    drop_via_button: "Drop Paths Via",
                    purge_queues_button: "Purge Announce Queues",
                },
                rnpath_trace: {
                    placeholder: "Enter 32-char destination hash...",
                    invalid_hash_hint: "Enter a valid destination hash",
                },
            },
        });

        axiosMock.get.mockImplementation((url) => {
            if (url.startsWith("/api/v1/rnpath/table")) {
                return Promise.resolve({
                    data: {
                        table: [
                            {
                                hash: "a".repeat(32),
                                hops: 1,
                                via: "b".repeat(32),
                                interface: "UDP",
                                expires: 1234567890,
                                state: 2,
                            },
                        ],
                        total: 1,
                        responsive: 1,
                        unresponsive: 0,
                    },
                });
            }
            if (url === "/api/v1/rnpath/rates") {
                return Promise.resolve({
                    data: {
                        rates: [
                            {
                                hash: "c".repeat(32),
                                last: 1234567890,
                                timestamps: [],
                                rate_violations: 0,
                                blocked_until: 0,
                            },
                        ],
                    },
                });
            }
            if (url === "/api/v1/reticulum/interfaces") {
                return Promise.resolve({
                    data: {
                        interfaces: { UDP: {} },
                    },
                });
            }
            if (url === "/api/v1/reticulum/discovered-interfaces") {
                return Promise.resolve({
                    data: {
                        interfaces: [{ name: "Discovered-IF" }],
                        active: [{ name: "Active-IF" }],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        axiosMock.post.mockResolvedValue({
            data: { success: true },
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("renders and loads path table data", async () => {
        render(RNPathPage);
        expect(screen.getByText("RNPath")).toBeTruthy();

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rnpath/table", expect.any(Object));
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rnpath/rates", expect.any(Object));
        });

        expect(await screen.findByText("Table")).toBeTruthy();
        expect(screen.getByText("Rates")).toBeTruthy();
        expect(screen.getByText("Actions")).toBeTruthy();
    });

    it("switches tabs to Rates and Actions", async () => {
        render(RNPathPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rnpath/table", expect.any(Object));
        });

        const ratesTab = screen.getByText("Rates");
        await fireEvent.click(ratesTab);
        expect(ratesTab.className).toContain("text-sem-accent");

        const actionsTab = screen.getByText("Actions");
        await fireEvent.click(actionsTab);
        expect(actionsTab.className).toContain("text-sem-accent");
    });

    it("calls request path API on Actions tab", async () => {
        render(RNPathPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rnpath/table", expect.any(Object));
        });

        const actionsTab = screen.getByText("Actions");
        await fireEvent.click(actionsTab);

        const input = screen.getByPlaceholderText(/destination hash/i);
        await fireEvent.input(input, { target: { value: "d".repeat(32) } });

        const requestBtn = screen.getByRole("button", { name: /Request/i });
        await fireEvent.click(requestBtn);

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/rnpath/request", {
                destination_hash: "d".repeat(32),
            });
        });
    });
});
