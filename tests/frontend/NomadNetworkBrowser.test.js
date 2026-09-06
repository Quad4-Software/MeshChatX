// SPDX-License-Identifier: 0BSD
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NomadNetworkBrowser from "@/features/nomadnetwork/components/NomadNetworkBrowser.svelte";

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(() => true),
        isOpen: vi.fn(() => true),
        on: vi.fn(),
        off: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(async () => true),
        prompt: vi.fn(async () => null),
        alert: vi.fn(),
    },
}));

describe("NomadNetworkBrowser.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn((url) => {
                if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
                if (url === "/api/v1/announces") {
                    return Promise.resolve({ data: { announces: [], total_count: 0 } });
                }
                if (url === "/api/v1/page-nodes") return Promise.resolve({ data: { nodes: [] } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn(() => Promise.resolve({ data: {} })),
            delete: vi.fn(() => Promise.resolve({ data: {} })),
        };
        window.api = axiosMock;
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("renders tabs and sidebar on mount", async () => {
        const { container } = render(NomadNetworkBrowser, {
            destinationHash: "aabbccddeeff00112233445566778899",
        });

        await waitFor(() => {
            expect(container.querySelector(".nomad-tab-bar")).toBeTruthy();
        });
    });

    it("fetches nomadnetwork.node announces not page-nodes", async () => {
        render(NomadNetworkBrowser);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(
                "/api/v1/announces",
                expect.objectContaining({
                    params: expect.objectContaining({ aspect: "nomadnetwork.node" }),
                })
            );
        });
        expect(axiosMock.get).not.toHaveBeenCalledWith("/api/v1/page-nodes");
    });

    it("creates a new tab when new tab button is clicked", async () => {
        const { container, getByTitle } = render(NomadNetworkBrowser);

        const newTabBtn = getByTitle(/new tab|nomadnet\.new_tab/i);
        await fireEvent.click(newTabBtn);

        const tabs = container.querySelectorAll('[role="tab"]');
        expect(tabs.length).toBeGreaterThanOrEqual(1);
    });

    it("creates a private tab when private tab button is clicked", async () => {
        const { container, getByTitle } = render(NomadNetworkBrowser);

        const newPrivateTabBtn = getByTitle(/private tab|nomadnet\.new_private_tab/i);
        await fireEvent.click(newPrivateTabBtn);

        const tabs = container.querySelectorAll('[role="tab"]');
        expect(tabs.length).toBeGreaterThanOrEqual(1);
    });

    it("keeps previously selected tab mounted after switching", async () => {
        const hashA = "aabbccddeeff00112233445566778899";
        const hashB = "11223344556677889900aabbccddeeff";
        const { container, getByTitle } = render(NomadNetworkBrowser, {
            destinationHash: hashA,
        });

        await waitFor(() => {
            expect(container.querySelector(".nomad-tab-bar")).toBeTruthy();
        });

        await fireEvent.click(getByTitle(/new tab|nomadnet\.new_tab/i));
        const tabButtons = container.querySelectorAll('[role="tab"]');
        expect(tabButtons.length).toBeGreaterThanOrEqual(2);

        await fireEvent.click(tabButtons[0]);
        await fireEvent.click(tabButtons[1]);

        const hosts = container.querySelectorAll(".absolute.inset-0");
        expect(hosts.length).toBeGreaterThanOrEqual(2);
    });

    it("honours routeQuery path and archive_id for archives handoff", async () => {
        const hash = "aabbccddeeff00112233445566778899";
        axiosMock.get.mockImplementation((url) => {
            if (url === `/api/v1/nomadnet/archives/42`) {
                return Promise.resolve({
                    data: {
                        archive: {
                            id: 42,
                            content: "# archived",
                            created_at: "2024-01-01T00:00:00Z",
                            page_path: "/page/old.mu",
                            hash: "deadbeef",
                        },
                    },
                });
            }
            if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [], total_count: 0 } });
            }
            return Promise.resolve({ data: {} });
        });

        render(NomadNetworkBrowser, {
            destinationHash: hash,
            routeQuery: { path: "/page/old.mu", archive_id: "42" },
        });

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(`/api/v1/nomadnet/archives/42`);
        });
    });
});
