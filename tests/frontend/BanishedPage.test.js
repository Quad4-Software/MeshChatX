import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import BlockedPage from "@/features/blocked/BlockedPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";

describe("BlockedPage.svelte (Banished UI)", () => {
    let axiosMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages({
            banishment: {
                title: "Banished",
                description: "Manage Banished users and nodes",
                lift_banishment: "Lift Banishment",
                user: "User",
                node: "Node",
                banished_at: "Banished at",
                no_items: "None",
                search_placeholder: "Search",
                filter_all_types: "All",
                filter_rns: "RNS",
                sort_newest: "Newest",
                sort_oldest: "Oldest",
                sort_name: "Name",
                result_count: "{count}",
                blocked_destinations: "Dests",
                lift_banishment_confirm: "Confirm {name}",
                banishment_lifted: "Lifted",
                failed_lift_banishment: "Fail",
                failed_load_banished: "Fail load",
            },
            common: { select: "Select", cancel: "Cancel", refresh: "Refresh" },
            archives: { select_all: "All" },
            nomadnet: { no_announces_yet: "empty", no_search_results_peers: "none" },
            call: { unknown: "Unknown" },
        });

        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/blocked-destinations") {
                return Promise.resolve({
                    data: {
                        blocked_destinations: [
                            { destination_hash: "a".repeat(32), created_at: "2026-01-04T12:00:00Z" },
                        ],
                    },
                });
            }
            if (url === "/api/v1/reticulum/blackhole") {
                return Promise.resolve({
                    data: {
                        blackholed_identities: {
                            ["b".repeat(32)]: {
                                source: "c".repeat(32),
                                reason: "Spam",
                                until: null,
                            },
                        },
                    },
                });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("displays Banished title and subtext", async () => {
        const { getByText } = render(BlockedPage);
        await waitFor(() => {
            expect(getByText("Banished")).toBeTruthy();
            expect(getByText("Manage Banished users and nodes")).toBeTruthy();
        });
    });

    it("combines local blocked and RNS blackholed items", async () => {
        const { getByText, container } = render(BlockedPage);
        await waitFor(() => expect(getByText("RNS Blackhole")).toBeTruthy());
        expect(container.textContent).toContain("a".repeat(32));
        expect(container.textContent).toContain("b".repeat(32));
        expect(container.textContent).toContain("Spam");
    });

    it("displays RNS Blackhole badge for blackholed items", async () => {
        const { getByText } = render(BlockedPage);
        await waitFor(() => expect(getByText("RNS Blackhole")).toBeTruthy());
    });

    it("calls delete API when lifting banishment", async () => {
        const DialogUtils = await import("@/js/DialogUtils");
        vi.spyOn(DialogUtils.default, "confirm").mockResolvedValue(true);

        const { findAllByText } = render(BlockedPage);
        const unblockButtons = await findAllByText("Lift Banishment");
        expect(unblockButtons.length).toBeGreaterThan(0);
        await fireEvent.click(unblockButtons[0]);
        await waitFor(() => expect(axiosMock.delete).toHaveBeenCalled());
    });
});
