import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayChatPage from "@/components/relay/RelayChatPage.vue";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import { mountToolsPageGlobals } from "./testI18n.js";
import { useConfigStore } from "@/js/stores/configStore.js";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(),
        prompt: vi.fn(() => Promise.resolve(null)),
    },
}));

vi.mock("@/js/NotificationUtils", () => ({
    default: {
        clearMessageNotifications: vi.fn(),
        clearAllMessageNotifications: vi.fn(),
        showNewMessageNotification: vi.fn(),
        syncAndroidNotificationContext: vi.fn(),
    },
}));

vi.mock("@/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
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

describe("bug-hunt regressions", () => {
    let axiosMock;

    beforeEach(() => {
        useConfigStore().config.theme = "light";
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

        const localStorageMock = {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        };
        vi.stubGlobal("localStorage", localStorageMock);
        window.URL.createObjectURL = vi.fn(() => "mock-url");
    });

    afterEach(() => {
        delete window.api;
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    const mountRelayPage = () => mount(RelayChatPage, { global: mountToolsPageGlobals() });

    const mountConversationViewer = () =>
        mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: "peer-hash", display_name: "Peer" },
                myLxmfAddressHash: "my-hash",
                conversations: [],
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
                mocks: {
                    $t: (key) => key,
                    $route: { meta: {} },
                    $router: { push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    AddImageButton: true,
                    AddAudioButton: true,
                    SendMessageButton: true,
                    ConversationDropDownMenu: true,
                    PaperMessageModal: true,
                    AudioWaveformPlayer: true,
                    LxmfUserIcon: true,
                },
            },
        });

    it("ConversationViewer drops the outbound send queue on identity switch", async () => {
        const wrapper = mountConversationViewer();
        const queue = wrapper.vm._outboundQueue;
        expect(queue).toBeTruthy();
        const clearSpy = vi.spyOn(queue, "clear");
        wrapper.vm.onIdentitySwitched({ identity_hash: "new-identity" });
        expect(clearSpy).toHaveBeenCalled();
        wrapper.unmount();
    });

    it("RelayChatPage refreshMembers ignores a response for a stale room", async () => {
        const wrapper = mountRelayPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        wrapper.vm.selectedHubHash = "hubA";
        wrapper.vm.selectedRoom = "roomA";
        wrapper.vm.members = [{ hash: "current" }];

        let resolveRefresh;
        const deferred = new Promise((resolve) => {
            resolveRefresh = resolve;
        });
        axiosMock.get.mockImplementationOnce((url) => {
            if (url.includes("/rooms/") && url.endsWith("/messages")) {
                return deferred;
            }
            return Promise.resolve({ data: {} });
        });

        const pending = wrapper.vm.refreshMembers();
        // User navigates to a different room before the response lands.
        wrapper.vm.selectedRoom = "roomB";
        resolveRefresh({ data: { members: [{ hash: "stale-room-member" }] } });
        await pending;

        expect(wrapper.vm.members).toEqual([{ hash: "current" }]);
        wrapper.unmount();
    });

    it("RelayChatPage refreshMembers still applies for the selected room", async () => {
        const wrapper = mountRelayPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        wrapper.vm.selectedHubHash = "hubA";
        wrapper.vm.selectedRoom = "roomA";

        let resolveRefresh;
        const deferred = new Promise((resolve) => {
            resolveRefresh = resolve;
        });
        axiosMock.get.mockImplementationOnce((url) => {
            if (url.includes("/rooms/") && url.endsWith("/messages")) {
                return deferred;
            }
            return Promise.resolve({ data: {} });
        });

        const pending = wrapper.vm.refreshMembers();
        resolveRefresh({ data: { members: [{ hash: "fresh" }] } });
        await pending;

        expect(wrapper.vm.members).toEqual([{ hash: "fresh" }]);
        wrapper.unmount();
    });

    it("RelayChatPage identity switch bumps roomSelectSequence", async () => {
        const wrapper = mountRelayPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        const seq = wrapper.vm.roomSelectSequence;
        wrapper.vm.onIdentitySwitched();
        expect(wrapper.vm.roomSelectSequence).toBeGreaterThan(seq);
        wrapper.unmount();
    });

    it("RelayChatPage in-flight selectRoom does not merge messages across identity switch", async () => {
        const wrapper = mountRelayPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        let resolveLoad;
        const deferred = new Promise((resolve) => {
            resolveLoad = resolve;
        });
        axiosMock.get.mockImplementationOnce(() => deferred);

        const pending = wrapper.vm.selectRoom(HUB_HASH, "roomA");
        wrapper.vm.onIdentitySwitched();
        resolveLoad({
            data: {
                messages: [{ kind: "msg", room: "roomA", src: "aa", nick: "x", text: "stale", ts: 1 }],
                members: [],
            },
        });
        await pending;

        expect(wrapper.vm.messages).toEqual([]);
        wrapper.unmount();
    });
});
