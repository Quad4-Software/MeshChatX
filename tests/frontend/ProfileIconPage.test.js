// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ProfileIconPage from "@/features/profile/ProfileIconPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";
import ToastUtils from "@/js/ToastUtils.js";
import { filterIconNames, normalizeHexColour } from "@/features/profile/lib/profileIcon.ts";

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

describe("ProfileIconPage.svelte", () => {
    let api;

    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages(en);
        api = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/config") {
                    return Promise.resolve({
                        data: {
                            config: {
                                lxmf_user_icon_name: "account",
                                lxmf_user_icon_foreground_colour: "#ffffff",
                                lxmf_user_icon_background_colour: "#000000",
                            },
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            patch: vi.fn().mockImplementation((_url, data) => {
                return Promise.resolve({
                    data: {
                        config: {
                            lxmf_user_icon_name: data.lxmf_user_icon_name,
                            lxmf_user_icon_foreground_colour: data.lxmf_user_icon_foreground_colour,
                            lxmf_user_icon_background_colour: data.lxmf_user_icon_background_colour,
                        },
                    },
                });
            }),
        };
        window.api = api;
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("fetches config on mount and renders preview", async () => {
        render(ProfileIconPage);
        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith("/api/v1/config");
        });
        expect(screen.getByText("Profile Icon Customizer")).toBeTruthy();
    });

    it("filters icon names by search input", async () => {
        render(ProfileIconPage);
        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith("/api/v1/config");
        });
        const input = screen.getByPlaceholderText(/Search \d+ icons\.\.\./);
        await fireEvent.input(input, { target: { value: "heart" } });
        expect(screen.getByText("heart")).toBeTruthy();
    });

    it("saves icon changes when save button is clicked", async () => {
        render(ProfileIconPage);
        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith("/api/v1/config");
        });

        const input = screen.getByPlaceholderText(/Search \d+ icons\.\.\./);
        await fireEvent.input(input, { target: { value: "robot" } });
        const robotBtn = await screen.findByText("robot");
        await fireEvent.click(robotBtn);

        const saveBtn = screen.getByText("Save");
        await fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(api.patch).toHaveBeenCalledWith(
                "/api/v1/config",
                expect.objectContaining({
                    lxmf_user_icon_name: "robot",
                })
            );
        });
        expect(ToastUtils.success).toHaveBeenCalledWith("Profile icon saved successfully");
    });

    it("removes profile icon when remove button clicked", async () => {
        render(ProfileIconPage);
        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith("/api/v1/config");
        });

        const removeBtn = screen.getByRole("button", { name: /Remove Icon/i });
        await fireEvent.click(removeBtn);

        await waitFor(() => {
            expect(api.patch).toHaveBeenCalledWith("/api/v1/config", {
                lxmf_user_icon_name: null,
                lxmf_user_icon_foreground_colour: null,
                lxmf_user_icon_background_colour: null,
            });
        });
        expect(ToastUtils.success).toHaveBeenCalledWith("Profile icon removed successfully");
    });
});

describe("profileIcon lib helpers", () => {
    it("normalizeHexColour normalizes valid hex codes", () => {
        expect(normalizeHexColour("#FFFFFF")).toBe("#ffffff");
        expect(normalizeHexColour("#123456ff")).toBe("#123456");
        expect(normalizeHexColour("invalid")).toBe("");
        expect(normalizeHexColour(null)).toBe("");
    });

    it("filterIconNames filters and limits names", () => {
        const names = ["account", "account-alert", "bell", "car"];
        expect(filterIconNames(names, "account", 10)).toEqual(["account", "account-alert"]);
        expect(filterIconNames(names, "", 2)).toEqual(["account", "account-alert"]);
    });
});
