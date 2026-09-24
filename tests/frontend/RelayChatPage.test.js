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
        vi.restoreAllMocks();
    });

    const mountPage = () => mount(RelayChatPage, { global: mountToolsPageGlobals() });

    it("loads and renders hubs", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        expect(wrapper.text()).toContain("Test Hub");
        expect(wrapper.vm.selectedHubHash).toBe(HUB_HASH);
    });

    it("keeps host visible and renders bots and search icon-only below md", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        // All tabs stay in the bar. Bots and search collapse to icons below md
        // so the bar never scrolls horizontally on phones.
        const tabs = wrapper.findAll('[role="tab"]');
        expect(tabs).toHaveLength(5);

        const hostTab = tabs.find((t) => t.text().trim() === "Host");
        expect(hostTab).toBeTruthy();
        expect(hostTab.classes()).toContain("inline-flex");

        for (const label of ["Bots", "Search"]) {
            const tab = tabs.find((t) => t.attributes("aria-label") === label);
            expect(tab, `${label} tab should be icon-only below md`).toBeTruthy();
            const span = tab.find("span");
            expect(span.classes()).toContain("hidden");
            expect(span.classes()).toContain("md:inline");
        }
    });

    it("shows hub rooms discovered via auto-list that have not been joined yet", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: { hubs: [makeHub({ available_rooms: { lobby: "Main", random: null } })] },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [makeHostedHub()] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [makeAnnounce()] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        // "lobby" is already joined (known_rooms), so only "random" is unjoined.
        expect(wrapper.vm.availableRoomsFor(wrapper.vm.hubs[0])).toEqual([
            { name: "random", topic: null, has_key: false },
        ]);
        expect(wrapper.text()).toContain("random");
    });

    it("joins an unjoined available room via the API when clicked", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(DialogUtils, "prompt").mockResolvedValue("");
        vi.spyOn(ToastUtils, "info").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "success").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: { hubs: [makeHub({ available_rooms: { random: null } })] },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [makeHostedHub()] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [makeAnnounce()] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        await wrapper.vm.joinAvailableRoom(wrapper.vm.hubs[0], "random");

        expect(DialogUtils.prompt).not.toHaveBeenCalled();
        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms`, {
            room: "random",
            remember: true,
        });
    });

    it("prompts for a key when a listed room is marked +k", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(DialogUtils, "prompt").mockResolvedValue("hunter2");
        vi.spyOn(ToastUtils, "info").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "success").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: {
                        hubs: [
                            makeHub({
                                available_rooms: { vault: null },
                                available_keyed_rooms: ["vault"],
                            }),
                        ],
                    },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        await wrapper.vm.joinAvailableRoom(wrapper.vm.hubs[0], "vault");

        expect(DialogUtils.prompt).toHaveBeenCalledWith(expect.stringContaining("vault"), "", {
            inputType: "password",
        });
        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms`, {
            room: "vault",
            remember: true,
            key: "hunter2",
        });
    });

    it("does not join a keyed available room when the key prompt is cancelled", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        vi.spyOn(DialogUtils, "prompt").mockResolvedValue(null);
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: {
                        hubs: [
                            makeHub({
                                available_rooms: { vault: null },
                                available_keyed_rooms: ["vault"],
                            }),
                        ],
                    },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        axiosMock.post.mockClear();

        await wrapper.vm.joinAvailableRoom(wrapper.vm.hubs[0], "vault");

        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("skips the key prompt when an available room already has a stored key", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(DialogUtils, "prompt").mockResolvedValue("unused");
        vi.spyOn(ToastUtils, "info").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "success").mockImplementation(() => {});
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: {
                        hubs: [
                            makeHub({
                                available_rooms: { vault: null },
                                stored_key_rooms: ["vault"],
                                available_keyed_rooms: ["vault"],
                            }),
                        ],
                    },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        await wrapper.vm.joinAvailableRoom(wrapper.vm.hubs[0], "vault");

        expect(DialogUtils.prompt).not.toHaveBeenCalled();
        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms`, {
            room: "vault",
            remember: true,
        });
    });

    it("refreshes available rooms via the rooms list API", async () => {
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(ToastUtils, "info").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: {
                        hubs: [
                            makeHub({
                                connected: true,
                                available_rooms: { lobby: "Main", random: null },
                            }),
                        ],
                    },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        axiosMock.post.mockResolvedValueOnce({
            data: { message: "Room list requested", hub: makeHub() },
        });

        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        await wrapper.vm.refreshAvailableRooms(wrapper.vm.hubs[0]);

        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms/list`);
        expect(ToastUtils.info).toHaveBeenCalled();
        expect(wrapper.vm.isRefreshingAvailableRooms(HUB_HASH)).toBe(false);
    });

    it("does not request a room list refresh when the hub is disconnected", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: {
                        hubs: [
                            makeHub({
                                connected: false,
                                status: 0,
                                available_rooms: { random: null },
                            }),
                        ],
                    },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        axiosMock.post.mockClear();

        await wrapper.vm.refreshAvailableRooms(wrapper.vm.hubs[0]);

        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("includes an optional room key when joining a room", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        wrapper.vm.joinRoomForm(wrapper.vm.hubs[0]).name = "vault";
        wrapper.vm.joinRoomForm(wrapper.vm.hubs[0]).key = "hunter2";
        await wrapper.vm.joinRoom(wrapper.vm.hubs[0]);
        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms`, {
            room: "vault",
            remember: true,
            key: "hunter2",
        });
        expect(wrapper.vm.joinRoomForm(wrapper.vm.hubs[0]).name).toBe("");
        expect(wrapper.vm.joinRoomForm(wrapper.vm.hubs[0]).key).toBe("");
    });

    it("keeps join room inputs independent per hub", async () => {
        const OTHER_HUB_HASH = "ffeeddccbbaa00112233445566778899";
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: {
                        hubs: [makeHub(), makeHub({ hub_hash: OTHER_HUB_HASH, name: "Other Hub" })],
                    },
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
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(2));

        const nameInputs = wrapper.findAll("input[data-rrc-join-name]");
        expect(nameInputs.length).toBe(2);

        const first = nameInputs.find((el) => el.attributes("data-rrc-join-name") === HUB_HASH);
        const second = nameInputs.find((el) => el.attributes("data-rrc-join-name") === OTHER_HUB_HASH);
        await first.setValue("alpha-room");
        expect(wrapper.vm.joinRoomForm(wrapper.vm.hubs[0]).name).toBe("alpha-room");
        expect(wrapper.vm.joinRoomForm(wrapper.vm.hubs[1]).name).toBe("");
        expect(second.element.value).toBe("");

        await wrapper.vm.joinRoom(wrapper.vm.hubs[0]);
        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms`, {
            room: "alpha-room",
            remember: true,
        });
        expect(wrapper.vm.joinRoomForm(wrapper.vm.hubs[0]).name).toBe("");
    });

    it("does not request messages or read receipts for a removed hub", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        vi.spyOn(DialogUtils, "confirm").mockResolvedValue(true);
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(ToastUtils, "success").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});

        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.selectedRoom).toBe("lobby"));
        axiosMock.get.mockClear();
        axiosMock.post.mockClear();

        let resolveDelete;
        axiosMock.delete.mockImplementationOnce(() => new Promise((r) => (resolveDelete = r)));
        const removal = wrapper.vm.removeHub(wrapper.vm.hubs[0]);
        await vi.waitFor(() => expect(axiosMock.delete).toHaveBeenCalled());

        // A websocket event for the hub landing mid-delete must not hit the API.
        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rrc.message",
                hub_hash: HUB_HASH,
                room: "lobby",
                message: { kind: "system", room: "lobby", text: "disconnected", ts: 2 },
            }),
        });
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
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(0));
        expect(wrapper.vm.selectedHubHash).toBe(null);
        expect(wrapper.vm.selectedRoom).toBe(null);
    });

    it("does not request messages or read receipts for a removed room", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        vi.spyOn(DialogUtils, "confirmCustom").mockResolvedValue(true);
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(ToastUtils, "success").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});

        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.selectedRoom).toBe("lobby"));
        axiosMock.get.mockClear();
        axiosMock.post.mockClear();

        let resolveDelete;
        axiosMock.delete.mockImplementationOnce(() => new Promise((r) => (resolveDelete = r)));
        const leaving = wrapper.vm.leaveRoom();
        await vi.waitFor(() => expect(axiosMock.delete).toHaveBeenCalled());

        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rrc.message",
                hub_hash: HUB_HASH,
                room: "lobby",
                message: { kind: "msg", room: "lobby", src: "aabb", text: "late", ts: 2 },
            }),
        });
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
        expect(wrapper.vm.selectedRoom).toBe(null);
    });

    it("clears a stale selection when the hub disappears from the listing", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.selectedRoom).toBe("lobby"));

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        await wrapper.vm.fetchHubs();
        expect(wrapper.vm.selectedHubHash).toBe(null);
        expect(wrapper.vm.selectedRoom).toBe(null);
    });

    it("prompts for a password after a bad key websocket error", async () => {
        const DialogUtils = (await import("@/js/DialogUtils")).default;
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        vi.spyOn(DialogUtils, "prompt").mockResolvedValue("correct-key");
        vi.spyOn(ToastUtils, "warning").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "info").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});
        vi.spyOn(ToastUtils, "success").mockImplementation(() => {});

        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rrc.message",
                hub_hash: HUB_HASH,
                room: "vault",
                message: {
                    kind: "error",
                    room: "vault",
                    text: "bad key (+k)",
                },
            }),
        });

        await vi.waitFor(() =>
            expect(DialogUtils.prompt).toHaveBeenCalledWith(expect.stringContaining("vault"), "", {
                inputType: "password",
            })
        );
        await vi.waitFor(() =>
            expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms`, {
                room: "vault",
                remember: true,
                key: "correct-key",
            })
        );
        expect(axiosMock.delete).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms/vault/key`);
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
        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms/lobby/read`);
    });

    it("shows hub motd inline in the room header", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.messages.length).toBe(1));
        wrapper.vm.hubs[0].motd = "Be kind to each other";
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("Be kind to each other");
    });

    it("member rows render avatar initials and copy the hash on context menu", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(wrapper.vm.members.length).toBe(1));
        wrapper.vm.showMembers = true;
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("carol");
        expect(wrapper.vm.memberInitial("carol")).toBe("C");
        expect(wrapper.vm.memberInitial("<abc123>")).toBe("A");
        expect(wrapper.vm.memberInitial("")).toBe("?");

        await wrapper.vm.copyMemberHash({ hash: "aabb", name: "carol" });
        expect(writeText).toHaveBeenCalledWith("aabb");
        delete navigator.clipboard;
    });

    it("openMemberDm resolves the LXMF address and navigates to messages", async () => {
        const wrapper = mountPage();
        const lxmfHash = "d".repeat(64);
        window.api.get.mockImplementation((url) => {
            if (url === "/api/v1/identity/" + "e".repeat(64) + "/lxmf-address") {
                return Promise.resolve({
                    data: { lxmf_destination_hash: lxmfHash, has_path: true },
                });
            }
            return Promise.resolve({ data: {} });
        });
        const push = vi.fn();
        wrapper.vm.$router = { push };

        await wrapper.vm.openMemberDm({ hash: "e".repeat(64), name: "carol" });
        expect(push).toHaveBeenCalledWith({ name: "messages", params: { destinationHash: lxmfHash } });
        expect(wrapper.vm.memberDmLoadingHash).toBeNull();
    });

    it("openMemberDm requests a path when the LXMF address has none", async () => {
        const wrapper = mountPage();
        const lxmfHash = "f".repeat(64);
        window.api.get.mockResolvedValue({
            data: { lxmf_destination_hash: lxmfHash, has_path: false },
        });
        window.api.post.mockResolvedValue({ data: {} });
        const push = vi.fn();
        wrapper.vm.$router = { push };

        await wrapper.vm.openMemberDm({ hash: "1".repeat(64), name: "dan" });
        expect(window.api.post).toHaveBeenCalledWith(`/api/v1/destination/${lxmfHash}/path`);
        expect(push).toHaveBeenCalledWith({ name: "messages", params: { destinationHash: lxmfHash } });
    });

    it("openMemberDm shows an error toast when no LXMF address can be derived", async () => {
        const wrapper = mountPage();
        window.api.get.mockRejectedValue({ response: { status: 404, data: { message: "none" } } });
        const push = vi.fn();
        wrapper.vm.$router = { push };

        await wrapper.vm.openMemberDm({ hash: "2".repeat(64), name: "eve" });
        expect(push).not.toHaveBeenCalled();
        expect(wrapper.vm.memberDmLoadingHash).toBeNull();
    });

    it("clears local mention unread when marking an open room read", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        wrapper.vm.hubs = [
            makeHub({
                mention_rooms: ["lobby"],
                unread_rooms: ["lobby"],
                unread_counts: { lobby: 2 },
                total_unread: 2,
            }),
        ];
        wrapper.vm.updateUnreadBadge();
        expect(wrapper.vm.hubs[0].mention_rooms).toEqual(["lobby"]);

        await wrapper.vm.markRoomRead(HUB_HASH, "lobby", { refreshHubs: false });

        expect(wrapper.vm.hubs[0].mention_rooms).toEqual([]);
        expect(wrapper.vm.hubs[0].unread_rooms).toEqual([]);
        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms/lobby/read`);
    });

    it("keeps websocket messages that arrive while selectRoom is loading", async () => {
        let resolveMessages;
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
                return new Promise((resolve) => {
                    resolveMessages = resolve;
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));

        const selectPromise = wrapper.vm.selectRoom(HUB_HASH, "lobby");
        await vi.waitFor(() => expect(typeof resolveMessages).toBe("function"));

        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rrc.message",
                hub_hash: HUB_HASH,
                room: "lobby",
                message: {
                    kind: "msg",
                    room: "lobby",
                    src: "live",
                    nick: "live",
                    text: "during-load",
                    ts: 99,
                    seq: 99,
                    mention: false,
                },
            }),
        });
        expect(wrapper.vm.messages.some((m) => m.text === "during-load")).toBe(true);

        resolveMessages({
            data: {
                messages: [
                    {
                        kind: "msg",
                        room: "lobby",
                        src: "aabb",
                        nick: "carol",
                        text: "hello",
                        ts: 1,
                        seq: 1,
                        mention: false,
                    },
                ],
                members: [{ hash: "aabb", name: "carol" }],
                has_more: false,
            },
        });
        await selectPromise;

        expect(wrapper.vm.messages.map((m) => m.text)).toEqual(["hello", "during-load"]);
    });

    it("dedupes websocket messages that already exist by seq", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        wrapper.vm.messages = [
            {
                kind: "msg",
                room: "lobby",
                src: "aabb",
                nick: "carol",
                text: "hello",
                ts: 1,
                seq: 5,
                mention: false,
            },
        ];

        wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "rrc.message",
                hub_hash: HUB_HASH,
                room: "lobby",
                message: {
                    kind: "msg",
                    room: "lobby",
                    src: "aabb",
                    nick: "carol",
                    text: "hello",
                    ts: 1,
                    seq: 5,
                    mention: false,
                },
            }),
        });

        expect(wrapper.vm.messages).toHaveLength(1);
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

        wrapper.vm.createHubForm = {
            name: "Fresh Hub",
            greeting: "hi",
            announce: true,
            announce_interval_seconds: 1800,
        };
        await wrapper.vm.createServerHub();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/rrc/servers", {
            name: "Fresh Hub",
            greeting: "hi",
            announce: true,
            announce_interval_seconds: 1800,
        });
    });

    it("saves hosted hub settings via the API", async () => {
        axiosMock.patch.mockResolvedValueOnce({ data: { hub: makeHostedHub({ name: "Renamed" }) } });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));

        wrapper.vm.openHostHubSettings(wrapper.vm.serverHubs[0]);
        wrapper.vm.hostHubSettingsForm = {
            name: "Renamed",
            announce: false,
            announce_interval_seconds: 900,
        };
        await wrapper.vm.saveHostHubSettings();

        expect(axiosMock.patch).toHaveBeenCalledWith(`/api/v1/rrc/servers/${HOSTED_HUB_ID}`, {
            name: "Renamed",
            announce: false,
            announce_interval_seconds: 900,
        });
    });

    it("preserves a zero announce interval when opening hosted hub settings", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({
                    data: { hubs: [makeHostedHub({ announce_interval_seconds: 0 })] },
                });
            }
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));

        wrapper.vm.openHostHubSettings(wrapper.vm.serverHubs[0]);
        expect(wrapper.vm.hostHubSettingsForm.announce_interval_seconds).toBe(0);
        expect(wrapper.vm.hostAnnounceIntervalMinutes).toBe(0);
    });

    it("saves a zero announce interval for hosted hub settings", async () => {
        axiosMock.patch.mockResolvedValueOnce({
            data: { hub: makeHostedHub({ announce_interval_seconds: 0 }) },
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));

        wrapper.vm.openHostHubSettings(wrapper.vm.serverHubs[0]);
        wrapper.vm.hostHubSettingsForm.announce_interval_seconds = 0;
        wrapper.vm.hostAnnounceIntervalDraft = "0";
        wrapper.vm.onHostAnnounceIntervalBlur();
        await wrapper.vm.saveHostHubSettings();

        expect(axiosMock.patch).toHaveBeenCalledWith(`/api/v1/rrc/servers/${HOSTED_HUB_ID}`, {
            name: "My Hub",
            announce: true,
            announce_interval_seconds: 0,
        });
    });

    it("toggles available rooms collapse and persists layout", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rrc/hubs") {
                return Promise.resolve({
                    data: { hubs: [makeHub({ available_rooms: { lobby: "Main", random: null } })] },
                });
            }
            if (url === "/api/v1/rrc/servers") {
                return Promise.resolve({ data: { hubs: [] } });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        expect(wrapper.vm.isAvailableRoomsExpanded(HUB_HASH)).toBe(true);
        wrapper.vm.toggleAvailableRooms(HUB_HASH);
        expect(wrapper.vm.isAvailableRoomsExpanded(HUB_HASH)).toBe(false);
        expect(wrapper.vm.availableRoomsExpanded[HUB_HASH]).toBe(false);
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
        wrapper.vm.showMembers = true;

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

    it("joins a hosted hub as a client from the host card action", async () => {
        axiosMock.post.mockResolvedValue({
            data: { hub: makeHub({ hub_hash: "aabbccddeeff00112233445566778899" }) },
        });
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.serverHubs.length).toBe(1));
        const hosted = wrapper.vm.serverHubs[0];
        await wrapper.vm.joinHostedAsClient(hosted);
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/rrc/hubs",
            expect.objectContaining({
                hub_hash: hosted.dest_hash,
                connect: true,
            })
        );
        expect(wrapper.vm.view).toBe("chat");
        expect(wrapper.vm.selectedHubHash).toBe(hosted.dest_hash);
    });

    it("keeps destination aspect collapsed in the add-hub dialog by default", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        wrapper.vm.openAddHub();
        expect(wrapper.vm.showAddHub).toBe(true);
        expect(wrapper.vm.addHubAdvancedOpen).toBe(false);
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

    it("isBadKeyErrorText requires bad key wording not bare +k", () => {
        const wrapper = mountPage();
        expect(wrapper.vm.isBadKeyErrorText("bad key (+k)")).toBe(true);
        expect(wrapper.vm.isBadKeyErrorText("ERROR: Bad Key (+K)")).toBe(true);
        expect(wrapper.vm.isBadKeyErrorText("failed: enable +k first")).toBe(false);
        expect(wrapper.vm.isBadKeyErrorText("+k")).toBe(false);
    });

    it("back from a room opened via search returns to the search view", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        wrapper.vm.view = "search";

        await wrapper.vm.openSearchResult({ hubHash: HUB_HASH, room: "lobby" });
        expect(wrapper.vm.view).toBe("chat");
        expect(wrapper.vm.selectedRoom).toBe("lobby");

        wrapper.vm.onBackFromRoom();
        expect(wrapper.vm.selectedRoom).toBe(null);
        expect(wrapper.vm.view).toBe("search");
    });

    it("back from a room opened via chat stays on the chat view", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
        await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        expect(wrapper.vm.view).toBe("chat");

        wrapper.vm.onBackFromRoom();
        expect(wrapper.vm.view).toBe("chat");
    });

    it("sendModerationCommand prefers peer hash over display nick", async () => {
        const wrapper = mountPage();
        await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBeGreaterThan(0));
        wrapper.vm.selectedHubHash = HUB_HASH;
        wrapper.vm.selectedRoom = "lobby";
        axiosMock.post.mockResolvedValueOnce({ data: {} });
        await wrapper.vm.sendModerationCommand("/kick {room} {target}", {
            src: "aabbccddeeff00112233445566778899",
            nick: "Alice With Spaces",
            text: "hi",
        });
        expect(axiosMock.post).toHaveBeenCalledWith(
            `/api/v1/rrc/hubs/${HUB_HASH}/command`,
            expect.objectContaining({
                text: "/kick lobby aabbccddeeff00112233445566778899",
                room: "lobby",
            })
        );
    });

    describe("chat UX enhancements", () => {
        const openRoom = async (wrapper) => {
            await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
            await wrapper.vm.selectRoom(HUB_HASH, "lobby");
        };

        const liveMsg = (overrides = {}) => ({
            kind: "msg",
            room: "lobby",
            src: "cc".repeat(16),
            nick: "burger",
            text: "hi",
            ts: Date.now(),
            mention: false,
            ...overrides,
        });

        beforeEach(() => {
            localStorage.clear();
        });

        describe("new messages pill", () => {
            it("tracks near-bottom state from scroll reports", () => {
                const wrapper = mountPage();
                wrapper.vm._onMessagesScrollState(500);
                expect(wrapper.vm.relayAtBottom).toBe(false);
                wrapper.vm.newMessagesBelow = 3;
                wrapper.vm._onMessagesScrollState(10);
                expect(wrapper.vm.relayAtBottom).toBe(true);
                expect(wrapper.vm.newMessagesBelow).toBe(0);
            });

            it("increments pending count instead of auto-scrolling when scrolled up", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                const scrollSpy = vi.spyOn(wrapper.vm, "scrollToBottom");
                wrapper.vm.relayAtBottom = false;

                wrapper.vm.onRrcMessage({ hub_hash: HUB_HASH, room: "lobby", message: liveMsg() });
                expect(wrapper.vm.newMessagesBelow).toBe(1);
                expect(scrollSpy).not.toHaveBeenCalled();

                wrapper.vm.onRrcMessage({ hub_hash: HUB_HASH, room: "lobby", message: liveMsg({ text: "two" }) });
                expect(wrapper.vm.newMessagesBelow).toBe(2);
            });

            it("auto-scrolls live arrivals when near the bottom", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                const scrollSpy = vi.spyOn(wrapper.vm, "scrollToBottom");
                wrapper.vm.relayAtBottom = true;

                wrapper.vm.onRrcMessage({ hub_hash: HUB_HASH, room: "lobby", message: liveMsg() });
                expect(scrollSpy).toHaveBeenCalledTimes(1);
                expect(wrapper.vm.newMessagesBelow).toBe(0);
            });

            it("presence and system arrivals do not inflate the pill count", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.relayAtBottom = false;
                wrapper.vm.onRrcMessage({
                    hub_hash: HUB_HASH,
                    room: "lobby",
                    message: { kind: "system", room: "lobby", text: "x joined", ts: 1 },
                });
                expect(wrapper.vm.newMessagesBelow).toBe(0);
            });

            it("scrollToBottom resets the pending count and re-follows", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.relayAtBottom = false;
                wrapper.vm.newMessagesBelow = 5;
                wrapper.vm.scrollToBottom();
                expect(wrapper.vm.relayAtBottom).toBe(true);
                expect(wrapper.vm.newMessagesBelow).toBe(0);
            });
        });

        describe("rrc:// deep links", () => {
            it("openRelayRoomLink joins the linked hub and room", async () => {
                const wrapper = mountPage();
                await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
                const selectSpy = vi.spyOn(wrapper.vm, "selectRoom");
                await wrapper.vm.openRelayRoomLink(`rrc://${HUB_HASH}/lobby`);
                expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/rrc/hubs/${HUB_HASH}/rooms`, {
                    room: "lobby",
                });
                expect(selectSpy).toHaveBeenCalledWith(HUB_HASH, "lobby");
            });

            it("openRelayRoomLink rejects malformed links", async () => {
                const ToastUtils = (await import("@/js/ToastUtils")).default;
                const errSpy = vi.spyOn(ToastUtils, "error").mockImplementation(() => {});
                const wrapper = mountPage();
                await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
                await vi.waitFor(() => expect(wrapper.vm.selectedRoom).toBe("lobby"));
                const before = wrapper.vm.selectedRoom;
                await wrapper.vm.openRelayRoomLink("rrc://nothex/lobby");
                expect(errSpy).toHaveBeenCalled();
                expect(wrapper.vm.selectedRoom).toBe(before);
            });

            it("renders rrc links clickable inside message html", () => {
                const wrapper = mountPage();
                const html = wrapper.vm.renderMessageHtml(`join rrc://${HUB_HASH}/lobby`);
                expect(html).toContain("rrc-link");
                expect(html).toContain(`data-rrc-url="rrc://${HUB_HASH}/lobby"`);
            });
        });

        describe("tab nick completion", () => {
            it("completes a member prefix at line start", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                const input = document.createElement("input");
                input.value = "car";
                input.setSelectionRange(3, 3);
                wrapper.vm.composer = "car";
                wrapper.vm.onComposerKeydown({ key: "Tab", target: input, preventDefault: vi.fn() });
                expect(wrapper.vm.composer).toBe("@carol: ");
            });

            it("cycles members on repeated tabs and resets on other keys", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                const input = document.createElement("input");
                input.value = "@";
                wrapper.vm.composer = "@";
                input.setSelectionRange(1, 1);
                wrapper.vm.onComposerKeydown({ key: "Tab", target: input, preventDefault: vi.fn() });
                expect(wrapper.vm.composer).toBe("@carol: ");
                wrapper.vm.onComposerKeydown({ key: "a", target: input });
                expect(wrapper.vm.nickCycle).toBe(null);
            });
        });

        describe("per-room drafts", () => {
            it("restores the draft when switching back to a room", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.composer = "half typed";
                await wrapper.vm.selectRoom(HUB_HASH, "other");
                expect(wrapper.vm.composer).toBe("");
                await wrapper.vm.selectRoom(HUB_HASH, "lobby");
                expect(wrapper.vm.composer).toBe("half typed");
            });

            it("clears the draft after a successful send", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.composer = "gone";
                await wrapper.vm.sendMessage();
                expect(wrapper.vm.composer).toBe("");
                await wrapper.vm.selectRoom(HUB_HASH, "other");
                await wrapper.vm.selectRoom(HUB_HASH, "lobby");
                expect(wrapper.vm.composer).toBe("");
            });

            it("saves an unsaved draft under the identity that loaded it on switch", async () => {
                const { useConfigStore } = await import("@/js/stores/configStore.js");
                useConfigStore().config = { identity_hash: "id-old" };
                const wrapper = mountPage();
                await openRoom(wrapper);
                // Typing without any save leaves lastDraftIdentityKey set only
                // because loadDraft recorded the loading identity.
                wrapper.vm.composer = "secret draft";
                useConfigStore().config = { identity_hash: "id-new" };
                wrapper.vm.onIdentitySwitched({ identity_hash: "id-new" });
                const stored = JSON.parse(localStorage.getItem("meshchat.drafts") || "{}");
                expect(stored["id-old"]?.[`${HUB_HASH}/lobby`]).toBe("secret draft");
                expect(stored["id-new"]).toBeUndefined();
                useConfigStore().config = {};
            });
        });

        describe("client-side ignore", () => {
            it("ignores a message author, purges their messages, and persists", async () => {
                const ToastUtils = (await import("@/js/ToastUtils")).default;
                vi.spyOn(ToastUtils, "info").mockImplementation(() => {});
                const wrapper = mountPage();
                await openRoom(wrapper);
                const msg = liveMsg({ src: "aabb", nick: "carol" });
                wrapper.vm.messageMenu = { show: true, x: 0, y: 0, msg };
                await wrapper.vm.toggleIgnoreFromMenu();

                expect(wrapper.vm.ignoredPeers).toEqual([{ hash: "aabb", name: "carol" }]);
                expect(wrapper.vm.isIgnoredMsg(liveMsg({ src: "aabb" }))).toBe(true);
                // The pre-existing lobby message from aabb is gone from the timeline.
                expect(wrapper.vm.messages.every((m) => m.src !== "aabb")).toBe(true);
                const stored = JSON.parse(localStorage.getItem("meshchatx.rrc.prefs"));
                expect(stored._.ignored).toEqual([{ hash: "aabb", name: "carol" }]);
            });

            it("persists prefs under the captured identity, not a switched live one", async () => {
                const { useConfigStore } = await import("@/js/stores/configStore.js");
                useConfigStore().config = { identity_hash: "id-old" };
                const wrapper = mountPage();
                await openRoom(wrapper);
                // Live config moves on without the switch handler having run
                // (a deferred save queued before the event landed).
                useConfigStore().config = { identity_hash: "id-new" };
                wrapper.vm.ignoredPeers = [{ hash: "aabb", name: "carol" }];
                wrapper.vm.persistRelayPrefs();
                const stored = JSON.parse(localStorage.getItem("meshchatx.rrc.prefs") || "{}");
                expect(stored["id-old"]?.ignored).toEqual([{ hash: "aabb", name: "carol" }]);
                expect(stored["id-new"]).toBeUndefined();
                useConfigStore().config = {};
            });

            it("reloads prefs under the real identity when config arrives after mount", async () => {
                const { useConfigStore } = await import("@/js/stores/configStore.js");
                // Mount before config resolves: prefs load under the "_" bucket.
                useConfigStore().config = {};
                localStorage.setItem(
                    "meshchatx.rrc.prefs",
                    JSON.stringify({ "id-real": { ignored: [], highlightWords: [], hideJoinPart: true } })
                );
                const wrapper = mountPage();
                await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
                expect(wrapper.vm.hideJoinPart).toBe(false);
                useConfigStore().config = { identity_hash: "id-real" };
                await vi.waitFor(() => expect(wrapper.vm.hideJoinPart).toBe(true));
                expect(wrapper.vm.relayPrefsLoadedKey).toBe("id-real");
                useConfigStore().config = {};
            });

            it("migrates prefs toggled during the config race into the real bucket", async () => {
                const { useConfigStore } = await import("@/js/stores/configStore.js");
                useConfigStore().config = {};
                const wrapper = mountPage();
                await vi.waitFor(() => expect(wrapper.vm.hubs.length).toBe(1));
                wrapper.vm.setHideJoinPart(true);
                expect(JSON.parse(localStorage.getItem("meshchatx.rrc.prefs") || "{}")._?.hideJoinPart).toBe(true);
                useConfigStore().config = { identity_hash: "id-real" };
                await vi.waitFor(() => expect(wrapper.vm.relayPrefsLoadedKey).toBe("id-real"));
                const stored = JSON.parse(localStorage.getItem("meshchatx.rrc.prefs") || "{}");
                expect(stored["id-real"]?.hideJoinPart).toBe(true);
                useConfigStore().config = {};
            });

            it("drops live pushes from ignored peers but keeps system rows", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.ignoredPeers = [{ hash: "aabb", name: "carol" }];
                const before = wrapper.vm.messages.length;
                wrapper.vm.onRrcMessage({ hub_hash: HUB_HASH, room: "lobby", message: liveMsg({ src: "aabb" }) });
                expect(wrapper.vm.messages.length).toBe(before);
                wrapper.vm.onRrcMessage({
                    hub_hash: HUB_HASH,
                    room: "lobby",
                    message: { kind: "system", text: "x joined", ts: 1 },
                });
                expect(wrapper.vm.messages.length).toBe(before + 1);
            });

            it("suppresses the toast for ignored messages in other rooms", async () => {
                const ToastUtils = (await import("@/js/ToastUtils")).default;
                const infoSpy = vi.spyOn(ToastUtils, "info").mockImplementation(() => {});
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.ignoredPeers = [{ hash: "aabb", name: "carol" }];
                wrapper.vm.onRrcMessage({ hub_hash: HUB_HASH, room: "other", message: liveMsg({ src: "aabb" }) });
                await vi.waitFor(() => expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rrc/hubs"));
                expect(infoSpy).not.toHaveBeenCalled();
            });

            it("canIgnoreMessageAuthor excludes own and system messages", async () => {
                const { useConfigStore } = await import("@/js/stores/configStore.js");
                useConfigStore().config = { identity_hash: "dd".repeat(16) };
                const wrapper = mountPage();
                await openRoom(wrapper);
                expect(wrapper.vm.canIgnoreMessageAuthor(liveMsg({ src: "dd".repeat(16) }))).toBe(false);
                expect(wrapper.vm.canIgnoreMessageAuthor({ kind: "system", text: "joined" })).toBe(false);
                expect(wrapper.vm.canIgnoreMessageAuthor(liveMsg())).toBe(true);
                useConfigStore().config = {};
            });

            it("unignoring from the menu restores messages via resync", async () => {
                const ToastUtils = (await import("@/js/ToastUtils")).default;
                vi.spyOn(ToastUtils, "info").mockImplementation(() => {});
                const wrapper = mountPage();
                await openRoom(wrapper);
                const msg = liveMsg({ src: "aabb", nick: "carol" });
                wrapper.vm.ignoredPeers = [{ hash: "aabb", name: "carol" }];
                wrapper.vm.messageMenu = { show: true, x: 0, y: 0, msg };
                await wrapper.vm.toggleIgnoreFromMenu();
                expect(wrapper.vm.ignoredPeers).toEqual([]);
                // The resync reloaded the room, bringing aabb's message back.
                await vi.waitFor(() => expect(wrapper.vm.messages.some((m) => m.src === "aabb")).toBe(true));
            });
        });

        describe("custom highlight words", () => {
            it("flags matching messages with the mention highlight", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWords = ["uucp"];
                const msg = liveMsg({ text: "anyone using uucp?" });
                wrapper.vm.applyLocalHighlightFlags([msg]);
                expect(msg.mention).toBe(true);
            });

            it("does not flag own, ignored, or already-mentioned messages", async () => {
                const { useConfigStore } = await import("@/js/stores/configStore.js");
                useConfigStore().config = { identity_hash: "dd".repeat(16) };
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWords = ["uucp"];
                wrapper.vm.ignoredPeers = [{ hash: "aabb", name: "carol" }];
                const own = liveMsg({ src: "dd".repeat(16), text: "uucp" });
                const ignored = liveMsg({ src: "aabb", text: "uucp" });
                const mentioned = liveMsg({ text: "uucp", mention: true });
                wrapper.vm.applyLocalHighlightFlags([own, ignored, mentioned]);
                expect(own.mention).toBe(false);
                expect(ignored.mention).toBe(false);
                expect(mentioned.mention).toBe(true);
                useConfigStore().config = {};
            });

            it("bumps the mention badge for matching messages in other rooms", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWords = ["callsign"];
                wrapper.vm.onRrcMessage({
                    hub_hash: HUB_HASH,
                    room: "other",
                    message: liveMsg({ room: "other", text: "what is your callsign" }),
                });
                await vi.waitFor(() => {
                    const hub = wrapper.vm.hubs.find((h) => h.hub_hash === HUB_HASH);
                    expect(hub.mention_rooms).toContain("other");
                });
            });

            it("bumps the mention badge for action messages in other rooms", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWords = ["callsign"];
                wrapper.vm.onRrcMessage({
                    hub_hash: HUB_HASH,
                    room: "other",
                    message: liveMsg({ kind: "action", room: "other", text: "waves their callsign" }),
                });
                await vi.waitFor(() => {
                    const hub = wrapper.vm.hubs.find((h) => h.hub_hash === HUB_HASH);
                    expect(hub.mention_rooms).toContain("other");
                });
            });

            it("keeps the local mention flag across hub refreshes", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWords = ["callsign"];
                wrapper.vm.onRrcMessage({
                    hub_hash: HUB_HASH,
                    room: "other",
                    message: liveMsg({ room: "other", text: "callsign check" }),
                });
                await vi.waitFor(() => {
                    const hub = wrapper.vm.hubs.find((h) => h.hub_hash === HUB_HASH);
                    expect(hub.mention_rooms).toContain("other");
                });
                // A later fetchHubs replaces the hubs array. The client-side
                // flag must survive or the badge silently drops.
                axiosMock.get.mockResolvedValueOnce({ data: { hubs: [makeHub()] } });
                await wrapper.vm.fetchHubs();
                const hub = wrapper.vm.hubs.find((h) => h.hub_hash === HUB_HASH);
                expect(hub.mention_rooms).toContain("other");
            });

            it("clears the local mention flag when the room is read", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWords = ["callsign"];
                wrapper.vm.onRrcMessage({
                    hub_hash: HUB_HASH,
                    room: "other",
                    message: liveMsg({ room: "other", text: "callsign check" }),
                });
                await vi.waitFor(() => {
                    const hub = wrapper.vm.hubs.find((h) => h.hub_hash === HUB_HASH);
                    expect(hub.mention_rooms).toContain("other");
                });
                wrapper.vm.clearLocalRoomUnread(HUB_HASH, "other");
                const hub = wrapper.vm.hubs.find((h) => h.hub_hash === HUB_HASH);
                expect(hub.mention_rooms || []).not.toContain("other");
                await wrapper.vm.fetchHubs();
                const hub2 = wrapper.vm.hubs.find((h) => h.hub_hash === HUB_HASH);
                expect(hub2.mention_rooms || []).not.toContain("other");
            });

            it("removing a word unflags previously highlighted messages", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWords = ["uucp"];
                const msg = liveMsg({ text: "anyone using uucp?" });
                wrapper.vm.messages = [msg];
                wrapper.vm.applyLocalHighlightFlags(wrapper.vm.messages);
                expect(msg.mention).toBe(true);
                wrapper.vm.removeHighlightWord("uucp");
                expect(msg.mention).toBe(false);
            });

            it("does not clear a server-set mention when a word is removed", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWords = ["uucp"];
                const serverMention = liveMsg({ text: "uucp fan", mention: true });
                wrapper.vm.messages = [serverMention];
                wrapper.vm.applyLocalHighlightFlags(wrapper.vm.messages);
                wrapper.vm.removeHighlightWord("uucp");
                expect(serverMention.mention).toBe(true);
            });

            it("adds and removes words through the prefs actions", async () => {
                const wrapper = mountPage();
                await openRoom(wrapper);
                wrapper.vm.highlightWordDraft = "  callsign  ";
                wrapper.vm.addHighlightWord();
                expect(wrapper.vm.highlightWords).toEqual(["callsign"]);
                wrapper.vm.highlightWordDraft = "callsign";
                wrapper.vm.addHighlightWord();
                expect(wrapper.vm.highlightWords).toEqual(["callsign"]);
                const stored = JSON.parse(localStorage.getItem("meshchatx.rrc.prefs"));
                expect(stored._.highlightWords).toEqual(["callsign"]);
                wrapper.vm.removeHighlightWord("callsign");
                expect(wrapper.vm.highlightWords).toEqual([]);
            });
        });
    });
});
