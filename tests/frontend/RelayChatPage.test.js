// SPDX-License-Identifier: 0BSD
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayChatPage from "@/features/relay-chat/components/RelayChatPage.svelte";
import { t, registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

const HUB_HASH = "00112233445566778899aabbccddeeff";
const HOSTED_HUB_ID = "deadbeefdeadbeefdeadbeefdeadbeef";

function makeHostedHub(overrides = {}) {
    return {
        id: HOSTED_HUB_ID,
        name: "My Hub",
        dest_hash: "aabbccddeeff00112233445566778899",
        enabled: true,
        running: true,
        announce: true,
        announce_interval_seconds: 900,
        uptime_seconds: 120,
        greeting: null,
        clients: 0,
        rooms: [{ name: "lobby", topic: "Chat", private: false, registered: true, members: 0 }],
        ...overrides,
    };
}

function makeAnnounce(overrides = {}) {
    return {
        destination_hash: "ffeeddccbbaa00112233445566778899",
        aspect: "rrc.hub",
        identity_hash: "1122334455667788",
        display_name: "Heard Hub",
        custom_display_name: null,
        hops: 2,
        updated_at: "2026-01-01 00:00:00",
        ...overrides,
    };
}

function makeHub(overrides = {}) {
    return {
        hub_hash: HUB_HASH,
        dest_name: "rrc.hub",
        name: "Test Hub",
        status: 2,
        connected: true,
        hub_name: "Test Hub",
        hub_version: "1",
        motd: null,
        rooms: ["lobby"],
        known_rooms: ["lobby"],
        unread_rooms: [],
        mention_rooms: [],
        available_rooms: {},
        auto_reconnect: false,
        auto_list: false,
        auto_who: false,
        nick_override: null,
        hub_icon: null,
        max_msg_body_bytes: 350,
        ...overrides,
    };
}

describe("RelayChatPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
        axiosMock = {
            get: vi.fn((url) => {
                if (url === "/api/v1/rrc/hubs") {
                    return Promise.resolve({ data: { hubs: [makeHub()] } });
                }
                if (url === "/api/v1/rrc/servers/active" || url === "/api/v1/rrc/servers") {
                    return Promise.resolve({ data: { server: makeHostedHub() } });
                }
                if (url === "/api/v1/rrc/discovery" || url === "/api/v1/announces") {
                    return Promise.resolve({ data: { announces: [makeAnnounce()], total_count: 1 } });
                }
                if (url.includes("/messages")) {
                    return Promise.resolve({
                        data: {
                            messages: [
                                {
                                    kind: "msg",
                                    room: "lobby",
                                    src: "aabb",
                                    nick: "carol",
                                    text: "hello",
                                    ts: 1,
                                    mention: false,
                                },
                            ],
                            members: [{ hash: "aabb", name: "carol" }],
                            has_more: false,
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
        vi.clearAllMocks();
        if (typeof globalThis.ResizeObserver !== "function") {
            globalThis.ResizeObserver = class {
                observe() {}
                unobserve() {}
                disconnect() {}
            };
        }
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("fetches hubs and servers on mount", async () => {
        render(RelayChatPage);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs");
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/servers/active");
        });
    });

    it("renders sidebar with hubs", async () => {
        const { getByText } = render(RelayChatPage);

        await waitFor(() => {
            expect(getByText("Test Hub")).toBeTruthy();
        });
    });

    it("switches to discovery view when clicking discovery button", async () => {
        const { getByText } = render(RelayChatPage);

        await waitFor(() => {
            expect(getByText(t("relay_chat.tab_discovery"))).toBeTruthy();
        });

        const discoverBtn = getByText(t("relay_chat.tab_discovery"));
        await fireEvent.click(discoverBtn);

        await waitFor(() => {
            expect(getByText("Heard Hub")).toBeTruthy();
        });
    });

    it("switches to host view when clicking host button", async () => {
        const { getByText } = render(RelayChatPage);

        await waitFor(() => {
            expect(getByText(t("relay_chat.tab_host"))).toBeTruthy();
        });

        const hostBtn = getByText(t("relay_chat.tab_host"));
        await fireEvent.click(hostBtn);

        await waitFor(() => {
            expect(getByText("My Hub")).toBeTruthy();
        });
    });

    it("collapses host, bots and search tabs into the mobile overflow menu", async () => {
        const { getByText, getAllByRole } = render(RelayChatPage);

        await waitFor(() => {
            expect(getByText("Test Hub")).toBeTruthy();
        });

        // Below md these tabs live in the overflow dropdown so the tab bar
        // never scrolls horizontally on phones.
        for (const key of ["tab_host", "tab_bots", "tab_search"]) {
            const tab = getByText(t(`relay_chat.${key}`)).closest("button");
            expect(tab.className).toContain("hidden");
            expect(tab.className).toContain("md:inline-flex");
        }

        // The overflow menu button is only for small screens and flags the
        // active view when an overflow tab is selected.
        const overflowBtn = getAllByRole("tab").find(
            (el) => el.getAttribute("aria-label") === t("messages.more_actions")
        );
        expect(overflowBtn).toBeTruthy();
        const searchTab = getByText(t("relay_chat.tab_search")).closest("button");
        await fireEvent.click(searchTab);
        await waitFor(() => {
            expect(overflowBtn.getAttribute("aria-selected")).toBe("true");
        });
    });

    it("back from a room opened via search returns to the search view", async () => {
        const { getByText, component } = render(RelayChatPage);

        await waitFor(() => {
            expect(getByText("Test Hub")).toBeTruthy();
        });

        const searchTab = getByText(t("relay_chat.tab_search")).closest("button");
        const chatTab = getByText(t("relay_chat.tab_chat")).closest("button");
        await fireEvent.click(searchTab);
        expect(searchTab.getAttribute("aria-selected")).toBe("true");

        component.openSearchResult({ hubHash: HUB_HASH, room: "lobby" });
        await waitFor(() => {
            expect(chatTab.getAttribute("aria-selected")).toBe("true");
        });

        component.onBackFromRoom();
        await waitFor(() => {
            expect(searchTab.getAttribute("aria-selected")).toBe("true");
        });
    });

    it("back from a room opened via chat stays on the chat view", async () => {
        const { getByText, component } = render(RelayChatPage);

        await waitFor(() => {
            expect(getByText("Test Hub")).toBeTruthy();
        });

        const chatTab = getByText(t("relay_chat.tab_chat")).closest("button");
        component.selectRoom({ hub_hash: HUB_HASH }, { name: "lobby" });
        await waitFor(() => {
            expect(chatTab.getAttribute("aria-selected")).toBe("true");
        });

        component.onBackFromRoom();
        await waitFor(() => {
            expect(chatTab.getAttribute("aria-selected")).toBe("true");
            expect(getByText(t("relay_chat.no_room_selected"))).toBeTruthy();
        });
    });
});
