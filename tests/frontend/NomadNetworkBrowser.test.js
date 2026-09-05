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

describe("NomadNetworkBrowser.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn((url) => {
                if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
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
            destinationHash: "aabbcc",
        });

        await waitFor(() => {
            expect(container.querySelector(".nomad-tab-bar")).toBeTruthy();
        });
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
});
