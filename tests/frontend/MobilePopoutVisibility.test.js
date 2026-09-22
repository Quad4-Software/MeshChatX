// SPDX-License-Identifier: 0BSD
import { render, cleanup } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayChatPage from "@/features/relay-chat/components/RelayChatPage.svelte";
import NomadNetworkPage from "@/features/nomadnetwork/components/NomadNetworkPage.svelte";

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
    },
}));

const HUB_HASH = "00112233445566778899aabbccddeeff";

function makeHub(overrides = {}) {
    return {
        hub_hash: HUB_HASH,
        name: "Test Hub",
        display_name: "Test Hub",
        rooms: ["lobby"],
        available_rooms: [],
        motd: null,
        max_msg_body_bytes: 350,
        ...overrides,
    };
}

describe("mobile popout visibility", () => {
    beforeEach(() => {
        vi.stubGlobal(
            "matchMedia",
            vi.fn().mockImplementation((query) => ({
                matches: false,
                media: query,
                addEventListener: vi.fn(),
                removeEventListener: vi.fn(),
                addListener: vi.fn(),
                removeListener: vi.fn(),
            }))
        );

        window.api = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/rrc/hubs") {
                    return Promise.resolve({ data: { hubs: [makeHub()] } });
                }
                if (url.includes("/messages")) {
                    return Promise.resolve({ data: { messages: [], has_more: false } });
                }
                if (url.includes("/members")) {
                    return Promise.resolve({ data: { members: [] } });
                }
                if (url === "/api/v1/favourites") {
                    return Promise.resolve({ data: { favourites: [] } });
                }
                if (url === "/api/v1/announces") {
                    return Promise.resolve({ data: { announces: [] } });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.unstubAllGlobals();
    });

    it("renders relay page without error", async () => {
        const { container } = render(RelayChatPage);
        expect(container).toBeTruthy();
    });

    it("renders nomad page without error", async () => {
        const { container } = render(NomadNetworkPage, {
            destinationHash: "",
        });
        expect(container).toBeTruthy();
    });
});
