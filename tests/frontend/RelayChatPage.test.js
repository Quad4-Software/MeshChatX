// SPDX-License-Identifier: 0BSD
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayChatPage from "@/features/relay-chat/components/RelayChatPage.svelte";
import { t, registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import GlobalState from "@/js/GlobalState.js";
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
        available_rooms: [],
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
                if (url === "/api/v1/rrc/servers") {
                    return Promise.resolve({ data: { hubs: [makeHostedHub()] } });
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
        window.localStorage.clear();
        GlobalState.config = {};
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
        GlobalState.config = {};
    });

    it("migrates prefs toggled during the config race into the real bucket", async () => {
        // Mount before config resolves: prefs load under the "_" bucket.
        GlobalState.config = {};
        render(RelayChatPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs");
        });
        window.localStorage.setItem(
            "meshchatx.rrc.prefs",
            JSON.stringify({ _: { ignored: [], highlightWords: [], hideJoinPart: true } })
        );
        GlobalState.config = { identity_hash: "id-real" };
        await waitFor(() => {
            const stored = JSON.parse(window.localStorage.getItem("meshchatx.rrc.prefs") || "{}");
            expect(stored["id-real"]?.hideJoinPart).toBe(true);
        });
    });

    it("does not overwrite an existing identity bucket on late config", async () => {
        GlobalState.config = {};
        window.localStorage.setItem(
            "meshchatx.rrc.prefs",
            JSON.stringify({
                _: { ignored: [], highlightWords: [], hideJoinPart: true },
                "id-real": { ignored: [{ hash: "aabb", name: "carol" }], highlightWords: [], hideJoinPart: false },
            })
        );
        render(RelayChatPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs");
        });
        GlobalState.config = { identity_hash: "id-real" };
        await waitFor(() => {
            // Give the subscription a turn; the real bucket must keep its prefs.
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs");
        });
        const stored = JSON.parse(window.localStorage.getItem("meshchatx.rrc.prefs") || "{}");
        expect(stored["id-real"]?.ignored).toEqual([{ hash: "aabb", name: "carol" }]);
        expect(stored["id-real"]?.hideJoinPart).toBe(false);
    });

    it("fetches hubs and servers on mount", async () => {
        render(RelayChatPage);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs");
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/servers");
        });
    });

    it("renders sidebar with hubs", async () => {
        const { getByText } = render(RelayChatPage);

        await waitFor(() => {
            expect(getByText("Test Hub")).toBeTruthy();
        });
    });

    it("keeps join room inputs independent per hub", async () => {
        const OTHER_HUB_HASH = "ffeeddccbbaa00112233445566778899";
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: { hubs: [makeHub(), makeHub({ hub_hash: OTHER_HUB_HASH, name: "Other Hub" })] },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [makeHostedHub()] } });
            }
            if (url === "/api/v1/rrc/discovery" || url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [makeAnnounce()], total_count: 1 } });
            }
            return Promise.resolve({ data: {} });
        });

        const { container, getByText } = render(RelayChatPage);
        await waitFor(() => expect(getByText("Other Hub")).toBeTruthy());

        // The second hub is collapsed by default; expand it so both join
        // forms render.
        await fireEvent.click(getByText("Other Hub"));
        await waitFor(() => {
            expect(container.querySelectorAll("input[data-rrc-join-name]").length).toBe(2);
        });

        const first = container.querySelector(`input[data-rrc-join-name="${HUB_HASH}"]`);
        const second = container.querySelector(`input[data-rrc-join-name="${OTHER_HUB_HASH}"]`);
        await fireEvent.input(first, { target: { value: "alpha-room" } });
        expect(first.value).toBe("alpha-room");
        expect(second.value).toBe("");
    });

    it("does not request messages or read receipts for a removed hub", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        const confirmSpy = vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(ToastUtils, "success").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});

        const { component } = render(RelayChatPage);
        await waitFor(() => expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs"));
        await component.selectRoom(HUB_HASH, "lobby");
        axiosMock.get.mockClear();
        axiosMock.post.mockClear();

        let resolveDelete;
        axiosMock.delete.mockImplementationOnce(() => new Promise((r) => (resolveDelete = r)));
        const removal = component.removeHub({ hub_hash: HUB_HASH });
        await waitFor(() => expect(axiosMock.delete).toHaveBeenCalled());

        // A websocket event for the hub landing mid-delete must not hit the API.
        component.onRrcMessage({
            hub_hash: HUB_HASH,
            room: "lobby",
            message: { kind: "system", room: "lobby", text: "disconnected", ts: 2 },
        });
        await Promise.resolve();
        expect(axiosMock.get).not.toHaveBeenCalledWith(
            expect.stringContaining(`/rrc/hubs/${HUB_HASH}/rooms/lobby/messages`)
        );
        expect(axiosMock.post).not.toHaveBeenCalledWith(
            expect.stringContaining(`/rrc/hubs/${HUB_HASH}/rooms/lobby/read`)
        );

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        resolveDelete({ data: {} });
        await removal;
        await waitFor(() => expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs"));
        confirmSpy.mockRestore();
    });

    it("does not request messages or read receipts for a removed room", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        const confirmSpy = vi.spyOn(DialogUtils, "confirmCustom").mockResolvedValue(true);
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(ToastUtils, "success").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});

        const { component } = render(RelayChatPage);
        await waitFor(() => expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs"));
        await component.selectRoom(HUB_HASH, "lobby");
        axiosMock.get.mockClear();
        axiosMock.post.mockClear();

        let resolveDelete;
        axiosMock.delete.mockImplementationOnce(() => new Promise((r) => (resolveDelete = r)));
        const leaving = component.leaveRoom();
        await waitFor(() => expect(axiosMock.delete).toHaveBeenCalled());

        component.onRrcMessage({
            hub_hash: HUB_HASH,
            room: "lobby",
            message: { kind: "msg", room: "lobby", src: "aabb", text: "late", ts: 2 },
        });
        await Promise.resolve();
        expect(axiosMock.post).not.toHaveBeenCalledWith(
            expect.stringContaining(`/rrc/hubs/${HUB_HASH}/rooms/lobby/read`)
        );

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [makeHub({ known_rooms: [], rooms: [] })] } });
            }
            return Promise.resolve({ data: {} });
        });
        resolveDelete({ data: {} });
        await leaving;
        confirmSpy.mockRestore();
    });

    it("clears a stale selection when the hub disappears from the listing", async () => {
        const { component, queryByText } = render(RelayChatPage);
        await waitFor(() => expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs"));
        await component.selectRoom(HUB_HASH, "lobby");

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        await component.fetchHubs();
        // The cleared selection drops the hub from the sidebar and the open
        // room view.
        await waitFor(() => {
            expect(queryByText("Test Hub")).toBeNull();
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

    it("stays on the discovery view after adding a discovered hub", async () => {
        axiosMock.post.mockResolvedValueOnce({ data: { hub: makeHub({ name: "Heard Hub" }) } });
        const { component, getByText } = render(RelayChatPage);
        await waitFor(() => expect(getByText(t("relay_chat.tab_discovery"))).toBeTruthy());
        const tab = getByText(t("relay_chat.tab_discovery")).closest("button");
        await fireEvent.click(tab);
        await waitFor(() => expect(tab.getAttribute("aria-selected")).toBe("true"));

        await component.addFromDiscovery(makeAnnounce());
        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/rrc/hubs", {
                hub_hash: makeAnnounce().destination_hash,
                name: "Heard Hub",
                dest_name: "rrc.hub",
                connect: true,
            });
        });
        // Adding must stay on discovery so several hubs can be added in a row.
        expect(tab.getAttribute("aria-selected")).toBe("true");
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
