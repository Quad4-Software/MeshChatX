// SPDX-License-Identifier: 0BSD

import { render, fireEvent, cleanup, screen } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import BotSetupPage from "../../meshchatx/src/frontend/features/bots/BotSetupPage.svelte";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
    },
}));

const TEMPLATES = [
    { id: "echo", name: "Echo Bot", description: "Echos messages", default_icon: "forum" },
    { id: "custom", name: "Custom Bot", description: "Your commands", default_icon: "robot" },
    { id: "rrc", name: "RRC Bot", description: "Relay rooms", default_icon: "chat" },
];

function makeApi() {
    return {
        get: vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/bots/status") {
                return Promise.resolve({ data: { status: { bots: [] }, templates: TEMPLATES } });
            }
            return Promise.resolve({ data: {} });
        }),
        post: vi.fn().mockResolvedValue({ data: { bot_id: "b1", success: true } }),
        patch: vi.fn(),
    };
}

describe("BotSetupPage.svelte", () => {
    let api;

    beforeEach(() => {
        api = makeApi();
        window.api = api;
        window.location.hash = "";
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("preselects the template from the route query", async () => {
        render(BotSetupPage, { props: { routeQuery: { template: "custom" } } });
        await vi.waitFor(() => expect(screen.getByDisplayValue("Custom Bot")).toBeTruthy());
    });

    it("creates a custom bot with commands and default icon", async () => {
        render(BotSetupPage, { props: { routeQuery: { template: "custom" } } });
        await vi.waitFor(() => expect(screen.getByDisplayValue("Custom Bot")).toBeTruthy());

        const nameInput = screen.getByDisplayValue("Custom Bot");
        await fireEvent.input(nameInput, { target: { value: "My Bot" } });

        await fireEvent.click(screen.getByText("Add command"));
        const cmdInput = screen.getByPlaceholderText("command");
        const respInput = screen.getByPlaceholderText("reply text");
        await fireEvent.input(cmdInput, { target: { value: "joke" } });
        await fireEvent.input(respInput, { target: { value: "ha" } });

        await fireEvent.click(screen.getByText("Create & Start"));

        await vi.waitFor(() =>
            expect(api.post).toHaveBeenCalledWith("/api/v1/bots/start", {
                template_id: "custom",
                name: "My Bot",
                icon: { icon_name: "robot", fg_color: "#6b7280", bg_color: "#e5e7eb" },
                custom: {
                    commands: [{ name: "joke", response: "ha" }],
                },
            })
        );
        expect(window.location.hash).toBe("#/bots");
    });

    it("blocks rrc creation without a valid hub hash", async () => {
        render(BotSetupPage, { props: { routeQuery: { template: "rrc" } } });
        await vi.waitFor(() => expect(screen.getByDisplayValue("RRC Bot")).toBeTruthy());

        const createBtn = screen.getByText("Create & Start");
        expect(createBtn.disabled).toBe(true);
    });
});
