// SPDX-License-Identifier: 0BSD

import { render, fireEvent, cleanup, screen, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayBotsPage from "../../meshchatx/src/frontend/features/relay-chat/components/RelayBotsPage.svelte";

const RRC_BOT = {
    id: "bot1",
    name: "Uptime Bot",
    template_id: "rrc",
    running: true,
    rrc: { hub: "aabbccddeeff00112233445566778899", rooms: ["general"], nick: "upbot" },
};

function makeApi(bots = []) {
    return {
        get: vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/bots/status") {
                return Promise.resolve({ data: { status: { bots } } });
            }
            return Promise.resolve({ data: {} });
        }),
        post: vi.fn().mockResolvedValue({ data: { success: true } }),
        patch: vi.fn().mockResolvedValue({ data: {} }),
        delete: vi.fn().mockResolvedValue({ data: {} }),
    };
}

describe("RelayBotsPage.svelte", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("lists only rrc-template bots", async () => {
        window.api = makeApi([
            RRC_BOT,
            { id: "b2", name: "Echo", template_id: "echo", running: false },
        ]);
        render(RelayBotsPage);
        await vi.waitFor(() => expect(screen.getByText("Uptime Bot")).toBeTruthy());
        expect(screen.queryByText("Echo")).toBeNull();
    });

    it("creates a bot with normalized rooms and rrc config", async () => {
        const api = makeApi();
        window.api = api;
        render(RelayBotsPage);
        await vi.waitFor(() => expect(screen.getByText("New Bot")).toBeTruthy());
        await fireEvent.click(screen.getByText("New Bot"));

        const nameInput = screen.getByText("Bot Name").closest("label").querySelector("input");
        await fireEvent.input(nameInput, { target: { value: "UpBot" } });
        const hubInput = screen.getByPlaceholderText("<hub destination hash>");
        await fireEvent.input(hubInput, { target: { value: "aabbccddeeff00112233445566778899" } });
        const roomsInput = screen.getByPlaceholderText("#general, #dev");
        await fireEvent.input(roomsInput, { target: { value: "#general,  #dev ,," } });

        await fireEvent.click(screen.getByText("Create bot"));

        const payload = api.post.mock.calls.find((c) => c[0] === "/api/v1/bots/start")?.[1];
        expect(payload).toBeTruthy();
        expect(payload.template_id).toBe("rrc");
        expect(payload.rrc.rooms).toEqual(["general", "dev"]);
        expect(payload.rrc.hub).toBe("aabbccddeeff00112233445566778899");
        expect(payload.rrc.mention_only).toBe(true);
    });

    it("uses the picked known hub over the custom hash input", async () => {
        window.api = makeApi();
        render(RelayBotsPage, {
            props: { knownHubs: [{ hash: "ff".repeat(16), name: "Hub" }] },
        });
        await vi.waitFor(() => expect(screen.getByText("New Bot")).toBeTruthy());
        await fireEvent.click(screen.getByText("New Bot"));

        const hubSelect = document.querySelector("select");
        await fireEvent.change(hubSelect, { target: { value: "ff".repeat(16) } });
        // Custom input is hidden once a hub is picked.
        expect(screen.queryByPlaceholderText("<hub destination hash>")).toBeNull();
    });

    it("stops a running bot via the stop endpoint", async () => {
        const api = makeApi([RRC_BOT]);
        window.api = api;
        render(RelayBotsPage);
        await vi.waitFor(() => expect(screen.getByText("Uptime Bot")).toBeTruthy());
        await fireEvent.click(screen.getByText("Stop"));
        expect(api.post).toHaveBeenCalledWith("/api/v1/bots/stop", { bot_id: "bot1" });
    });

    it("polls bot status while mounted", async () => {
        const api = makeApi([RRC_BOT]);
        window.api = api;
        render(RelayBotsPage);
        await vi.waitFor(() => expect(screen.getByText("Uptime Bot")).toBeTruthy());
        await vi.advanceTimersByTimeAsync(5000);
        const calls = api.get.mock.calls.filter((c) => c[0] === "/api/v1/bots/status");
        expect(calls.length).toBeGreaterThanOrEqual(2);
    });
});
