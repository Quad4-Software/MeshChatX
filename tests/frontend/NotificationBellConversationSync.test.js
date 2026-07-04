import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

let wsHandlers = {};
let emitterHandlers = {};

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn((event, handler) => {
            wsHandlers[event] = wsHandlers[event] || [];
            wsHandlers[event].push(handler);
        }),
        off: vi.fn((event, handler) => {
            if (wsHandlers[event]) {
                wsHandlers[event] = wsHandlers[event].filter((h) => h !== handler);
            }
        }),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn((event, handler) => {
            emitterHandlers[event] = emitterHandlers[event] || [];
            emitterHandlers[event].push(handler);
        }),
        off: vi.fn((event, handler) => {
            if (emitterHandlers[event]) {
                emitterHandlers[event] = emitterHandlers[event].filter((h) => h !== handler);
            }
        }),
        emit: vi.fn((event, payload) => {
            (emitterHandlers[event] || []).forEach((h) => h(payload));
        }),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: { formatTimeAgo: () => "1h ago" },
}));

import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";
import NotificationBell from "../../meshchatx/src/frontend/components/NotificationBell.vue";
import ConversationViewer from "../../meshchatx/src/frontend/components/messages/ConversationViewer.vue";

const MaterialDesignIcon = { template: '<div class="mdi"></div>', props: ["iconName"] };

const PEER_HASH = "bb".repeat(16);

function simulateWsDelivery() {
    const data = JSON.stringify({
        type: "lxmf.delivery",
        lxmf_message: { is_incoming: true, content: "hello", title: "", fields: {} },
    });
    (wsHandlers["message"] || []).forEach((h) => h({ data }));
}

function mountBell() {
    return mount(NotificationBell, {
        global: {
            components: { MaterialDesignIcon },
            directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
            mocks: {
                $router: { push: vi.fn() },
                $t: (key) => {
                    const map = {
                        "app.notifications_no_new": "No new notifications",
                        "app.notifications_empty_history": "No notification history",
                        "app.notifications_history_title": "Recent notification history",
                    };
                    return map[key] || key;
                },
            },
        },
    });
}

function mountViewer() {
    return mount(ConversationViewer, {
        props: {
            selectedPeer: { destination_hash: PEER_HASH, display_name: "Peer" },
            myLxmfAddressHash: "aa".repeat(16),
            conversations: [{ destination_hash: PEER_HASH, display_name: "Peer", is_unread: true }],
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
                ConversationPeerHeader: true,
                ConversationMessageEntry: true,
                ConversationMessageListVirtual: true,
            },
        },
    });
}

function createNotificationsApiMock() {
    let conversationRead = false;
    const get = vi.fn().mockImplementation((_url, config) => {
        const unreadOnly = config?.params?.unread === true;
        if (!conversationRead) {
            const item = {
                type: "lxmf_message",
                destination_hash: PEER_HASH,
                display_name: "Peer",
                latest_message_preview: "hello",
                updated_at: new Date().toISOString(),
            };
            return Promise.resolve({
                data: {
                    notifications: unreadOnly ? [item] : [item],
                    unread_count: 1,
                },
            });
        }
        return Promise.resolve({
            data: {
                notifications: [],
                unread_count: 0,
            },
        });
    });
    const post = vi.fn().mockImplementation((url) => {
        if (String(url).includes("/mark-as-read")) {
            conversationRead = true;
        }
        return Promise.resolve({ data: {} });
    });
    return {
        get,
        post,
        markRead: () => {
            conversationRead = true;
        },
        isRead: () => conversationRead,
    };
}

describe("NotificationBell conversation read sync", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        wsHandlers = {};
        emitterHandlers = {};
        window.URL.createObjectURL = vi.fn(() => "blob:mock");
        vi.stubGlobal(
            "FileReader",
            vi.fn(function () {
                return { readAsDataURL: vi.fn() };
            })
        );
        vi.stubGlobal("localStorage", {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        });
    });

    afterEach(() => {
        wsHandlers = {};
        emitterHandlers = {};
        vi.unstubAllGlobals();
    });

    it("reproduces stale badge: delivery raises count, read in Messages clears without opening bell", async () => {
        const api = createNotificationsApiMock();
        window.api = { get: api.get, post: api.post };

        const bell = mountBell();
        await flushPromises();
        expect(bell.vm.unreadCount).toBe(1);
        expect(bell.find("span.bg-red-500").exists()).toBe(true);

        simulateWsDelivery();
        await flushPromises();
        expect(bell.vm.unreadCount).toBe(1);

        const viewer = mountViewer();
        await flushPromises();
        const conversation = { destination_hash: PEER_HASH, is_unread: true };
        await viewer.vm.markConversationAsRead(conversation);
        await flushPromises();

        expect(api.post).toHaveBeenCalledWith(`/api/v1/lxmf/conversations/${PEER_HASH}/mark-as-read`);
        expect(GlobalEmitter.emit).toHaveBeenCalledWith("notifications-changed");
        expect(bell.vm.unreadCount).toBe(0);
        expect(bell.find("span.bg-red-500").exists()).toBe(false);

        bell.unmount();
        viewer.unmount();
    });

    it("stale badge clears on bell click when server already has zero unread (empty dropdown)", async () => {
        const api = createNotificationsApiMock();
        api.markRead();
        window.api = { get: api.get, post: api.post };

        const bell = mountBell();
        bell.vm.unreadCount = 3;
        await bell.vm.$nextTick();
        expect(bell.find("span.bg-red-500").text()).toBe("3");

        await bell.find("button").trigger("click");
        await flushPromises();
        await new Promise((r) => setTimeout(r, 80));

        expect(bell.vm.unreadCount).toBe(0);
        expect(bell.vm.notifications).toEqual([]);
        expect(document.body.textContent).toContain("No new notifications");

        const markCalls = api.post.mock.calls.filter((c) => c[0] === "/api/v1/notifications/mark-as-viewed");
        expect(markCalls).toHaveLength(0);

        bell.unmount();
    });

    it("background poll refreshes badge while dropdown stays closed", async () => {
        vi.useFakeTimers();
        const api = createNotificationsApiMock();
        window.api = { get: api.get, post: api.post };

        const bell = mountBell();
        await flushPromises();
        expect(bell.vm.unreadCount).toBe(1);

        api.markRead();
        await vi.advanceTimersByTimeAsync(5000);
        await flushPromises();

        expect(bell.vm.unreadCount).toBe(0);
        expect(bell.vm.isDropdownOpen).toBe(false);

        vi.useRealTimers();
        bell.unmount();
    });

    it("does not emit notifications-changed when mark-as-read API fails", async () => {
        const api = createNotificationsApiMock();
        api.post.mockImplementation((url) => {
            if (String(url).includes("/mark-as-read")) {
                return Promise.reject(new Error("network"));
            }
            return Promise.resolve({ data: {} });
        });
        window.api = { get: api.get, post: api.post };

        const viewer = mountViewer();
        await flushPromises();
        GlobalEmitter.emit.mockClear();

        const conversation = { destination_hash: PEER_HASH, is_unread: true };
        await viewer.vm.markConversationAsRead(conversation);
        await flushPromises();

        expect(GlobalEmitter.emit).not.toHaveBeenCalledWith("notifications-changed");
        expect(conversation.is_unread).toBe(false);

        viewer.unmount();
    });

    it("badge count tracks API unread_count after websocket delivery", async () => {
        let unread = 0;
        window.api = {
            get: vi.fn().mockImplementation(() =>
                Promise.resolve({
                    data: {
                        notifications:
                            unread > 0
                                ? [
                                      {
                                          type: "lxmf_message",
                                          destination_hash: PEER_HASH,
                                          display_name: "Peer",
                                          latest_message_preview: "ping",
                                      },
                                  ]
                                : [],
                        unread_count: unread,
                    },
                })
            ),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };

        const bell = mountBell();
        await flushPromises();
        expect(bell.vm.unreadCount).toBe(0);

        unread = 2;
        simulateWsDelivery();
        await flushPromises();
        expect(bell.vm.unreadCount).toBe(2);
        expect(bell.find("span.bg-red-500").text()).toBe("2");

        unread = 0;
        GlobalEmitter.emit("notifications-changed");
        await flushPromises();
        expect(bell.vm.unreadCount).toBe(0);

        bell.unmount();
    });
});
