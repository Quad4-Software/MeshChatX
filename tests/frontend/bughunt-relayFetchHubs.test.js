// SPDX-License-Identifier: 0BSD
// Bug-hunt: RelayChatPage.onRrcMessage calls fetchHubs() (REST GET /rrc/hubs)
// for EVERY websocket message that is not for the open room — no debounce.
import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayChatPage from "../../meshchatx/src/frontend/components/relay/RelayChatPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

const HUB_HASH = "00112233445566778899aabbccddeeff";
const OTHER_HUB = "ffeeddccbbaa00112233445566778899";

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

describe("bughunt: RelayChatPage fetchHubs spam", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
        window.localStorage.removeItem("meshchatx.relay.layout");
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [makeHub()] } });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            if (url.includes("/rooms/") && url.endsWith("/messages")) {
                return Promise.resolve({ data: { messages: [], members: [] } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
        vi.restoreAllMocks();
    });

    it("N off-room rrc.message events trigger N REST /rrc/hubs fetches", async () => {
        const wrapper = mount(RelayChatPage, { global: mountToolsPageGlobals() });
        await wrapper.vm.$nextTick();
        // Let mount-time fetches settle.
        await new Promise((r) => setTimeout(r, 30));
        axiosMock.get.mockClear();

        const N = 25;
        for (let i = 0; i < N; i++) {
            wrapper.vm.onWebsocketMessage({
                type: "rrc.message",
                hub_hash: OTHER_HUB,
                room: `room-${i % 3}`,
                message: { kind: "msg", seq: i + 1, text: "hi", ts: i, src: "aa".repeat(16) },
            });
        }
        await new Promise((r) => setTimeout(r, 30));

        const hubFetches = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/rrc/hubs");
        console.log(`off-room messages=${N} -> /rrc/hubs GETs=${hubFetches.length}`);
        // A sane implementation coalesces bursts into ~1 fetch. The current
        // code fires one REST call per message.
        expect(hubFetches.length, `expected coalesced hubs fetch, got ${hubFetches.length} for ${N} messages`)
            .toBeLessThanOrEqual(3);
        wrapper.unmount();
    });

    it("system/notice off-room messages also spam fetchHubs", async () => {
        const wrapper = mount(RelayChatPage, { global: mountToolsPageGlobals() });
        await wrapper.vm.$nextTick();
        await new Promise((r) => setTimeout(r, 30));
        axiosMock.get.mockClear();

        for (let i = 0; i < 10; i++) {
            wrapper.vm.onWebsocketMessage({
                type: "rrc.message",
                hub_hash: OTHER_HUB,
                room: "lobby",
                message: { kind: "system", event: "join", text: "x joined", ts: i },
            });
        }
        await new Promise((r) => setTimeout(r, 30));
        const hubFetches = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/rrc/hubs");
        console.log(`off-room system msgs=10 -> /rrc/hubs GETs=${hubFetches.length}`);
        expect(hubFetches.length).toBeLessThanOrEqual(3);
        wrapper.unmount();
    });
});
