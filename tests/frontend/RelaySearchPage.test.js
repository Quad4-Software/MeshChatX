// SPDX-License-Identifier: 0BSD

import { render, fireEvent, cleanup, screen, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelaySearchPage from "../../meshchatx/src/frontend/features/relay-chat/components/RelaySearchPage.svelte";

const HITS = [
    {
        hub_hash: "aabbccddeeff00112233445566778899",
        hub_name: "Hub One",
        room: "lobby",
        nick: "alice",
        text: "hello world",
        ts: Date.now(),
        kind: "msg",
    },
    {
        hub_hash: "ffeeddccbbaa00112233445566778899",
        hub_name: "Hub Two",
        room: "dev",
        nick: "bob",
        text: "another hit",
        ts: Date.now(),
        kind: "msg",
    },
];

function makeApi() {
    return {
        get: vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/rrc/search") {
                return Promise.resolve({ data: { results: HITS } });
            }
            return Promise.resolve({ data: {} });
        }),
    };
}

async function typeQuery(value) {
    const input = screen.getByPlaceholderText("Search messages across all hubs…");
    await fireEvent.input(input, { target: { value } });
    await vi.advanceTimersByTimeAsync(300);
}

describe("RelaySearchPage.svelte", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("queries the global endpoint with the raw query string", async () => {
        const api = makeApi();
        window.api = api;
        render(RelaySearchPage);
        await typeQuery('from:alice "hello world" -spam');
        expect(api.get).toHaveBeenCalledWith("/api/v1/rrc/search", {
            params: { q: 'from:alice "hello world" -spam', limit: 100 },
        });
        await vi.waitFor(() => expect(screen.getAllByRole("button").length).toBeGreaterThanOrEqual(2));
    });

    it("calls onopenroom with hub and room when a result is clicked", async () => {
        window.api = makeApi();
        const onopenroom = vi.fn();
        render(RelaySearchPage, { props: { onopenroom } });
        await typeQuery("hello");
        await vi.waitFor(() => expect(screen.getByText("hello world")).toBeTruthy());
        const hit = screen.getByText("hello world");
        const btn = hit.closest("button");
        await fireEvent.click(btn);
        expect(onopenroom).toHaveBeenCalledWith({ hubHash: HITS[0].hub_hash, room: "lobby" });
    });

    it("skips the network call for an empty query", async () => {
        const api = makeApi();
        window.api = api;
        render(RelaySearchPage);
        await typeQuery("   ");
        expect(api.get).not.toHaveBeenCalledWith("/api/v1/rrc/search", expect.anything());
    });
});
