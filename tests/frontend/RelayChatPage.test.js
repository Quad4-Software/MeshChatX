import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RelayChatPage from "@/components/relay/RelayChatPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

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

describe("RelayChatPage.vue", () => {
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
                return Promise.resolve({ data: { hubs: [makeHostedHub()] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [makeAnnounce()] } });
            }
            if (url.includes("/rooms/") && url.endsWith("/messages")) {
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
                    },
                });
            }
            if (url.includes("/api/v1/rrc/servers/") && url.endsWith("/members")) {
                return Promise.resolve({
                    data: {
                        members: [
                            {
                                hash: "01010101010101010101010101010101",
                                name: "alice",
                                nick: "alice",
                                rooms: ["lobby"],
                            },
                        ],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
    });

    const mountPage = () => mount(RelayChatPage, { global: mountToolsPageGlobals() });

    it("loads and renders hubs", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        expect(wrapper.text()).toContain("Test Hub");
        expect(wrapper.vm.selectedHubHash).toBe(HUB_HASH);
    });

    it("loads messages and members when selecting a room", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.messages.length).toBe(1));

        expect(wrapper.vm.selectedRoom).toBe("lobby");
        expect(wrapper.vm.messages[0].text).toBe("hello");
        expect(wrapper.vm.members.length).toBe(1);
        expect(wrapper.text()).toContain("hello");
    });

    it("sends a message via the API", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");

        wrapper.vm.composer = "hi there";
        await wrapper.vm.sendMessage();

        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms/lobby/messages`, {
            text: "hi there",
        });
        expect(wrapper.vm.composer).toBe("");
    });

    it("sends an action message when prefixed with /me", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");

        wrapper.vm.composer = "/me waves";
        await wrapper.vm.sendMessage();

        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms/lobby/messages`, {
            text: "waves",
            action: true,
        });
    });

    it("appends incoming websocket messages for the active room", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.messages.length).toBe(1));

        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rrc.message",
                hub_hash: HUB_HASH,
                room: "lobby",
                message: {
                    kind: "msg",
                    room: "lobby",
                    src: "ccdd",
                    nick: "eve",
                    text: "incoming",
                    ts: 2,
                    mention: false,
                },
            }),
        });

        expect(wrapper.vm.messages.some((m) => m.text === "incoming")).toBe(true);
    });

    it("adds a hub via the API", async () => {
        axiosMock.post.mockResolvedValueOnce({ data: { hub: makeHub({ name: "New Hub" }) } });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        wrapper.vm.addHubForm = { hub_hash: HUB_HASH, name: "New Hub", dest_name: "" };
        await wrapper.vm.addHub();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/rrc/hubs", {
            hub_hash: HUB_HASH,
            name: "New Hub",
            dest_name: undefined,
            connect: true,
        });
    });

    it("loads hosted hubs for the host view", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));
        expect(wrapper.vm.serverHubs[0].name).toBe("My Hub");
        expect(wrapper.vm.roomForms[HOSTED_HUB_ID]).toEqual({ name: "", topic: "", private: false });
    });

    it("creates a hosted hub via the API", async () => {
        axiosMock.post.mockResolvedValueOnce({ data: { hub: makeHostedHub({ name: "Fresh Hub" }) } });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));

        wrapper.vm.createHubForm = { name: "Fresh Hub", greeting: "hi", announce: true };
        await wrapper.vm.createServerHub();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/rrc/servers", {
            name: "Fresh Hub",
            greeting: "hi",
            announce: true,
        });
    });

    it("creates a room on a hosted hub via the API", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));

        wrapper.vm.roomForms[HOSTED_HUB_ID] = { name: "general", topic: "talk", private: false };
        await wrapper.vm.createRoom(wrapper.vm.serverHubs[0]);

        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/servers/${HOSTED_HUB_ID}/rooms`, {
            name: "general",
            topic: "talk",
            private: false,
        });
    });

    it("loads discovered hubs for the discovery view", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.discovered.length).toBe(1));
        expect(wrapper.vm.discovered[0].display_name).toBe("Heard Hub");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announces", {
            params: { aspect: "rrc.hub", limit: 200, search: undefined },
        });
    });

    it("adds a hub from discovery via the API", async () => {
        axiosMock.post.mockResolvedValueOnce({ data: { hub: makeHub({ name: "Heard Hub" }) } });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.discovered.length).toBe(1));

        await wrapper.vm.addFromDiscovery(makeAnnounce());

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/rrc/hubs", {
            hub_hash: "ffeeddccbbaa00112233445566778899",
            name: "Heard Hub",
            dest_name: "rrc.hub",
            connect: true,
        });
        expect(wrapper.vm.view).toBe("chat");
    });

    it("upserts discovered hubs on an announce websocket event", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.discovered.length).toBe(1));

        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "announce",
                announce: makeAnnounce({
                    destination_hash: "abcabcabcabcabcabcabcabcabcabcab",
                    display_name: "New Heard",
                }),
            }),
        });

        expect(wrapper.vm.discovered.length).toBe(2);
        expect(wrapper.vm.discovered.some((n) => n.display_name === "New Heard")).toBe(true);
    });

    it("toggles hub expansion in the sidebar", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        expect(wrapper.vm.isExpanded(HUB_HASH)).toBe(true);
        wrapper.vm.toggleHub(HUB_HASH);
        expect(wrapper.vm.isExpanded(HUB_HASH)).toBe(false);
        wrapper.vm.toggleHub(HUB_HASH);
        expect(wrapper.vm.isExpanded(HUB_HASH)).toBe(true);
    });

    it("derives online and offline members", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.members.length).toBe(1));

        wrapper.vm.messages.push({
            kind: "msg",
            room: "lobby",
            src: " zzzz",
            nick: "dave",
            text: "earlier",
            ts: 0,
            mention: false,
        });

        expect(wrapper.vm.onlineMembers.map((m) => m.name)).toContain("carol");
        expect(wrapper.vm.offlineMembers.map((m) => m.name)).toContain("dave");
    });

    it("refreshes discovery and clears the loading flag", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.discovered.length).toBe(1));

        await wrapper.vm.refreshDiscovered();

        expect(wrapper.vm.discoveryLoading).toBe(false);
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announces", {
            params: { aspect: "rrc.hub", limit: 200, search: undefined },
        });
    });

    it("uses custom hub icon when configured", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: { hubs: [makeHub({ hub_icon: "satellite-uplink" })] },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [makeHostedHub()] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        expect(wrapper.vm.hubIconName(wrapper.vm.hubs[0])).toBe("satellite-uplink");
    });

    it("saves hub icon from settings", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        const hub = wrapper.vm.hubs[0];
        wrapper.vm.openSettings(hub);
        wrapper.vm.settingsForm.hub_icon = "server-network";
        await wrapper.vm.saveSettings();
        expect(axiosMock.patch).toHaveBeenCalledWith(
            `/api/v1/rrc/hubs/${HUB_HASH}`,
            expect.objectContaining({ hub_icon: "server-network" })
        );
    });

    it("loads hosted hub members when opening the moderation page", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));

        const hub = wrapper.vm.serverHubs[0];
        wrapper.vm.view = "host";
        wrapper.vm.openHostModeration(hub, { tab: "members", room: "lobby" });
        await wrapper.vm.$nextTick();

        const page = wrapper.findComponent({ name: "RelayHostModerationPage" });
        await vi.waitFor(() => expect(page.vm.members).toHaveLength(1));

        expect(axiosMock.get).toHaveBeenCalledWith(`/api/v1/rrc/servers/${HOSTED_HUB_ID}/members`, {
            params: { room: "lobby" },
        });
        expect(wrapper.vm.hostModeration.hub.id).toBe(HOSTED_HUB_ID);
        expect(page.vm.members[0].name).toBe("alice");
    });

    it("refreshes hosted hubs on a server change websocket event", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));
        axiosMock.get.mockClear();

        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({ type: "rrc.server.change", hub_id: HOSTED_HUB_ID }),
        });

        await vi.waitFor(() => expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/servers"));
    });
});
