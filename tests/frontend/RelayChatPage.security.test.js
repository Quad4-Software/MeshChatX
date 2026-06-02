// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayChatPage from "@/components/relay/RelayChatPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

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
        rooms: ["lobby"],
        known_rooms: ["lobby"],
        unread_rooms: [],
        mention_rooms: [],
        available_rooms: {},
        auto_reconnect: false,
        auto_list: false,
        auto_who: false,
        nick_override: null,
        max_msg_body_bytes: 350,
        ...overrides,
    };
}

describe("RelayChatPage security and fuzz", () => {
    let axiosMock;

    beforeEach(() => {
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
    });

    const mountPage = () => mount(RelayChatPage, { global: mountToolsPageGlobals() });

    it("encodeRoom percent-encodes path segments", () => {
        const wrapper = mountPage();
        expect(wrapper.vm.encodeRoom("a/b")).toBe("a%2Fb");
        expect(wrapper.vm.encodeRoom("../lobby")).toBe("..%2Flobby");
        expect(wrapper.vm.encodeRoom("lobby?x=1")).toBe("lobby%3Fx%3D1");
    });

    it("renders XSS-shaped message text as escaped text, not HTML", async () => {
        const xss = '<img src=x onerror="alert(1)">';
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/messages")) {
                return Promise.resolve({
                    data: {
                        messages: [
                            {
                                kind: "msg",
                                room: "lobby",
                                src: "aabb",
                                nick: "evil",
                                text: xss,
                                ts: 1,
                                mention: false,
                            },
                        ],
                        members: [],
                    },
                });
            }
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [makeHub()] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.messages.length).toBe(1));
        expect(wrapper.html()).toContain("&lt;img");
        expect(wrapper.html()).not.toMatch(/<img\s[^>]*onerror/i);
        expect(wrapper.text()).toContain("<img");
    });

    it("ignores malformed websocket payloads without throwing", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        const safePayloads = [
            { data: "not json" },
            { data: "" },
            { data: '{"type":' },
            { data: "[]" },
            { data: "{}" },
            { data: '{"type":"unknown"}' },
        ];
        for (const payload of safePayloads) {
            expect(() => wrapper.vm.onWebsocketMessage(payload)).not.toThrow();
        }
        expect(() => wrapper.vm.onWebsocketMessage({ data: "null" })).toThrow();
    });

    it("fuzz websocket event shapes without throwing", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        const before = wrapper.vm.messages.length;
        for (let i = 0; i < 50; i++) {
            const event = {
                data: JSON.stringify({
                    type: i % 3 === 0 ? "rrc.message" : i % 3 === 1 ? "rrc.change" : "other",
                    hub_hash: i % 2 === 0 ? HUB_HASH : "deadbeef".repeat(4),
                    room: i % 2 === 0 ? "lobby" : `room-${i}`,
                    message:
                        i % 4 === 0
                            ? {
                                  kind: "msg",
                                  text: `<script>${i}</script>`,
                                  ts: i,
                                  src: "xx",
                                  nick: `n${i}`,
                              }
                            : null,
                    announce: i % 5 === 0 ? { aspect: "rrc.hub", destination_hash: "ab".repeat(16) } : undefined,
                }),
            };
            expect(() => wrapper.vm.onWebsocketMessage(event)).not.toThrow();
        }
        expect(wrapper.vm.messages.length).toBeGreaterThanOrEqual(before);
    });

    it("does not append websocket messages for mismatched hub or room", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.selectedRoom).toBe("lobby"));
        const count = wrapper.vm.messages.length;
        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rrc.message",
                hub_hash: "ff".repeat(16),
                room: "lobby",
                message: {
                    kind: "msg",
                    room: "lobby",
                    src: "cc",
                    nick: "x",
                    text: "wrong hub",
                    ts: 9,
                    mention: false,
                },
            }),
        });
        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rrc.message",
                hub_hash: HUB_HASH,
                room: "other",
                message: {
                    kind: "msg",
                    room: "other",
                    src: "cc",
                    nick: "x",
                    text: "wrong room",
                    ts: 10,
                    mention: false,
                },
            }),
        });
        expect(wrapper.vm.messages.filter((m) => m.text === "wrong hub")).toHaveLength(0);
        expect(wrapper.vm.messages.filter((m) => m.text === "wrong room")).toHaveLength(0);
        expect(wrapper.vm.messages.length).toBe(count);
    });

    it("rejects prototype pollution keys in websocket JSON safely", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        const polluted =
            '{"type":"rrc.message","hub_hash":"' +
            HUB_HASH +
            '","room":"lobby","message":{"kind":"msg","text":"p","ts":1,"src":"a","nick":"n"},"__proto__":{"polluted":true}}';
        expect(() => wrapper.vm.onWebsocketMessage({ data: polluted })).not.toThrow();
        expect(Object.prototype.polluted).toBeUndefined();
    });

    it("sendMessage does not pass raw script tags unencoded in API path", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        wrapper.vm.composer = "hello";
        await wrapper.vm.sendMessage();
        const call = axiosMock.post.mock.calls.find((c) => c[0].includes("/messages"));
        expect(call).toBeDefined();
        expect(call[0]).toContain(encodeURIComponent("lobby"));
    });

    it("addHub strips unsafe hub_hash input before POST", async () => {
        axiosMock.post.mockResolvedValueOnce({ data: { hub: makeHub() } });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        wrapper.vm.addHubForm = {
            hub_hash: "  " + HUB_HASH + "  ",
            name: "Hub",
            dest_name: "",
        };
        await wrapper.vm.addHub();
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/rrc/hubs",
            expect.objectContaining({ hub_hash: HUB_HASH })
        );
    });
});
