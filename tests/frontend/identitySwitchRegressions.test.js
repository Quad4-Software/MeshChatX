// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/svelte";
import RelayChatPage from "@/features/relay-chat/components/RelayChatPage.svelte";
import ConversationViewer from "@/features/messages/components/ConversationViewer.svelte";
import GlobalEmitter from "@/js/GlobalEmitter.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

const queue = { clear: vi.fn(), enqueue: vi.fn(), cancelJob: vi.fn(), size: 0 };

vi.mock("@/js/outboundSendQueue.js", () => ({
    createOutboundQueue: () => queue,
}));

const HUB_HASH = "00112233445566778899aabbccddeeff";

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
        rooms: ["roomA", "roomB"],
        known_rooms: ["roomA", "roomB"],
        unread_rooms: [],
        mention_rooms: [],
        available_rooms: [],
        available_keyed_rooms: [],
        auto_reconnect: false,
        auto_list: false,
        auto_who: false,
        nick_override: null,
        hub_icon: null,
        max_msg_body_bytes: 350,
        ...overrides,
    };
}

describe("identity switch and stale-response regressions", () => {
    let axiosMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
        queue.clear.mockClear();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [makeHub()] } });
            }
            if (url === "/api/v1/rrc/servers/active" || url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { server: null } });
            }
            if (url === "/api/v1/rrc/discovery" || url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            if (url.includes("/rooms/") && url.endsWith("/messages")) {
                return Promise.resolve({ data: { messages: [], members: [], has_more: false } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it("ConversationViewer drops the outbound send queue on identity switch", async () => {
        const peerHash = "aa".repeat(16);
        render(ConversationViewer, {
            selectedPeer: { destination_hash: peerHash, display_name: "Peer" },
            myLxmfAddressHash: "bb".repeat(16),
            conversations: [],
        });
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalled();
        });
        queue.clear.mockClear();

        GlobalEmitter.emit("identity-switched", { identity_hash: "new-identity" });
        await waitFor(() => {
            expect(queue.clear).toHaveBeenCalled();
        });
    });

    it("RelayChatPage refreshMembers ignores a response for a stale room", async () => {
        const { component, getByText } = render(RelayChatPage);
        await waitFor(() => expect(getByText("Test Hub")).toBeTruthy());

        await component.selectRoom(HUB_HASH, "roomA");
        // The header member counter reads 0 for the empty member list.
        await waitFor(() => expect(getByText("0")).toBeTruthy());

        // websocket-reconnected triggers softResyncOpenRoom -> refreshMembers
        // when the messages payload carries no members array.
        let resolveMembers;
        const deferred = new Promise((resolve) => {
            resolveMembers = resolve;
        });
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/rooms/") && url.endsWith("/messages")) {
                return deferred;
            }
            return Promise.resolve({ data: {} });
        });
        GlobalEmitter.emit("websocket-reconnected", { degraded: false, failed: [] });
        await waitFor(() => {
            expect(
                axiosMock.get.mock.calls.some((c) => String(c[0]).includes("/rooms/roomA/messages"))
            ).toBe(true);
        });

        // User moves to roomB before the stale member fetch lands.
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [makeHub()] } });
            }
            if (url.includes("/rooms/") && url.endsWith("/messages")) {
                return Promise.resolve({
                    data: { messages: [], members: [{ hash: "roomb-member", name: "B" }], has_more: false },
                });
            }
            return Promise.resolve({ data: {} });
        });
        const selected = component.selectRoom(HUB_HASH, "roomB");
        resolveMembers({ data: { messages: [], members: [{ hash: "stale" }] } });
        await selected;
        await waitFor(() => expect(getByText("1")).toBeTruthy());
    });

    it("RelayChatPage in-flight selectRoom does not merge messages across identity switch", async () => {
        const { component, getByText, queryByText } = render(RelayChatPage);
        await waitFor(() => expect(getByText("Test Hub")).toBeTruthy());

        let resolveLoad;
        const deferred = new Promise((resolve) => {
            resolveLoad = resolve;
        });
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/rooms/") && url.endsWith("/messages")) {
                return deferred;
            }
            return Promise.resolve({ data: {} });
        });

        const pending = component.selectRoom(HUB_HASH, "roomA");
        GlobalEmitter.emit("identity-switched", { identity_hash: "new-identity" });
        resolveLoad({
            data: {
                messages: [
                    { kind: "msg", room: "roomA", src: "aa", nick: "x", text: "stale marker", ts: 1 },
                ],
                members: [],
            },
        });
        await pending;

        await waitFor(() => {
            expect(queryByText("stale marker")).toBeNull();
        });
    });
});
