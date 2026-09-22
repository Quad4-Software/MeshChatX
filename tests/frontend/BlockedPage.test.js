import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import BlockedPage from "../../meshchatx/src/frontend/features/blocked/BlockedPage.svelte";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.js";

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: { confirm: vi.fn().mockResolvedValue(true) },
}));
vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({ default: { success: vi.fn(), error: vi.fn() } }));
vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: { formatTimeAgo: () => "1h ago" },
}));

describe("BlockedPage UI", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            banishment: {
                title: "banishment.title",
                description: "banishment.description",
                no_items: "banishment.no_items",
                search_placeholder: "search",
                filter_all_types: "all",
                user: "user",
                node: "node",
                filter_rns: "rns",
                sort_newest: "newest",
                sort_oldest: "oldest",
                sort_name: "name",
                result_count: "{count}",
                lift_banishment: "lift",
                lift_selected: "lift {count}",
                lift_selected_confirm: "confirm {count}",
                lift_selected_success: "ok {count}",
                lift_banishment_confirm: "confirm {name}",
                banishment_lifted: "lifted",
                failed_lift_banishment: "fail",
                failed_load_banished: "fail load",
                banished_at: "at",
                blocked_destinations: "dests",
            },
            common: { select: "common.select", cancel: "common.cancel", refresh: "refresh" },
            archives: { select_all: "all" },
            nomadnet: { no_announces_yet: "nomadnet.no_announces_yet", no_search_results_peers: "none" },
            call: { unknown: "unknown" },
        });
        global.api = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/blocked-destinations")
                    return Promise.resolve({ data: { blocked_destinations: [] } });
                if (url === "/api/v1/reticulum/blackhole")
                    return Promise.resolve({ data: { blackholed_identities: {} } });
                return Promise.resolve({ data: {} });
            }),
            delete: vi.fn().mockResolvedValue({}),
        };
        window.api = global.api;
    });

    afterEach(() => {
        cleanup();
    });

    it("renders title and description", async () => {
        const { getByText } = render(BlockedPage);
        await waitFor(() => {
            expect(getByText("banishment.title")).toBeTruthy();
            expect(getByText("banishment.description")).toBeTruthy();
        });
    });

    it("renders search input and refresh button", async () => {
        const { container } = render(BlockedPage);
        await waitFor(() => {
            expect(container.querySelector('input[type="text"]')).toBeTruthy();
            expect(container.querySelector("button")).toBeTruthy();
        });
    });

    it("shows empty state after load", async () => {
        const { getByText } = render(BlockedPage);
        await waitFor(() => {
            expect(getByText("banishment.no_items")).toBeTruthy();
        });
    });

    it("renders blocked items when provided", async () => {
        window.api.get = vi.fn().mockImplementation((url, opts) => {
            if (url === "/api/v1/blocked-destinations")
                return Promise.resolve({ data: { blocked_destinations: [{ destination_hash: "abc123" }] } });
            if (url === "/api/v1/reticulum/blackhole") return Promise.resolve({ data: { blackholed_identities: {} } });
            if (url === "/api/v1/announces" && opts?.params?.destination_hash === "abc123")
                return Promise.resolve({
                    data: {
                        announces: [
                            {
                                destination_hash: "abc123",
                                display_name: "Blocked User",
                                identity_hash: "abc123",
                                aspect: "lxmf.delivery",
                            },
                        ],
                    },
                });
            return Promise.resolve({ data: {} });
        });
        global.api = window.api;
        const { findByText, container } = render(BlockedPage);
        expect(await findByText("Blocked User")).toBeTruthy();
        expect(container.textContent).toContain("abc123");
    });

    it("search input updates value", async () => {
        const { container } = render(BlockedPage);
        await waitFor(() => expect(container.querySelector('input[type="text"]')).toBeTruthy());
        const input = container.querySelector('input[type="text"]');
        await fireEvent.input(input, { target: { value: "test" } });
        expect(input.value).toBe("test");
    });

    it("supports multi-select mode for bulk unban", async () => {
        global.api.get = vi.fn().mockImplementation((url, opts) => {
            if (url === "/api/v1/blocked-destinations")
                return Promise.resolve({
                    data: {
                        blocked_destinations: [{ destination_hash: "abc123" }, { destination_hash: "def456" }],
                    },
                });
            if (url === "/api/v1/reticulum/blackhole") return Promise.resolve({ data: { blackholed_identities: {} } });
            if (url === "/api/v1/announces") {
                const hash = opts?.params?.destination_hash;
                return Promise.resolve({
                    data: {
                        announces: [
                            {
                                destination_hash: hash,
                                display_name: hash === "abc123" ? "User A" : "User B",
                                identity_hash: hash,
                                aspect: "lxmf.delivery",
                            },
                        ],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
        window.api = global.api;

        const { container, getByText } = render(BlockedPage);
        await waitFor(() => expect(getByText("User A")).toBeTruthy());

        expect(container.querySelectorAll('input[type="checkbox"]').length).toBe(0);
        await fireEvent.click(getByText("common.select"));
        await waitFor(() => expect(container.querySelectorAll('input[type="checkbox"]').length).toBeGreaterThan(0));

        const boxes = container.querySelectorAll('input[type="checkbox"]');
        for (const box of boxes) {
            if (box !== boxes[0] || boxes.length === 1) {
                await fireEvent.click(box);
            } else {
                await fireEvent.click(box);
            }
        }
        // Select both identity checkboxes (skip select-all if present as first)
        const identityBoxes = [...boxes].filter((b) => b.closest(".flex.min-h-0"));
        for (const box of identityBoxes) {
            if (!box.checked) {
                await fireEvent.click(box);
            }
        }

        const liftSelected = [...container.querySelectorAll("button")].find((b) => b.textContent.includes("lift"));
        expect(liftSelected).toBeTruthy();
        await fireEvent.click(liftSelected);
        await waitFor(() => expect(global.api.delete).toHaveBeenCalled());
    });
});
