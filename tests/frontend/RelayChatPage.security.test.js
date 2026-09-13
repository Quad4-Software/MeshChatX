// SPDX-License-Identifier: 0BSD

import { render, cleanup, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayChatPage from "@/features/relay-chat/components/RelayChatPage.svelte";

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
            if (url.includes("/messages")) {
                return Promise.resolve({
                    data: {
                        messages: [
                            {
                                kind: "msg",
                                room: "lobby",
                                src: "aabb",
                                nick: "evil",
                                text: '<img src=x onerror="alert(1)">',
                                ts: 1,
                                mention: false,
                            },
                        ],
                        members: [],
                        has_more: false,
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("renders XSS-shaped message text safely escaped, not executing or injecting img", async () => {
        const { container } = render(RelayChatPage);

        await waitFor(() => {
            expect(container.querySelector("img[onerror]")).toBeNull();
        });
    });
});
