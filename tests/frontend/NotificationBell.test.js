import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NotificationBell from "../../meshchatx/src/frontend/components/NotificationBell.vue";

let wsHandlers = {};
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

vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: { formatTimeAgo: (d) => "1h ago" },
}));

const MaterialDesignIcon = { template: '<div class="mdi"></div>', props: ["iconName"] };

function mountBell(options = {}) {
    return mount(NotificationBell, {
        global: {
            components: { MaterialDesignIcon },
            directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
            mocks: {
                $router: { push: vi.fn() },
            },
        },
        ...options,
    });
}

function simulateWsMessage(type, extra = {}) {
    const data = JSON.stringify({ type, ...extra });
    (wsHandlers["message"] || []).forEach((h) => h({ data }));
}

describe("NotificationBell UI", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        wsHandlers = {};
        global.axios.get = vi.fn().mockResolvedValue({ data: { notifications: [], unread_count: 0 } });
        global.axios.post = vi.fn().mockResolvedValue({ data: {} });
    });

    afterEach(() => {
        wsHandlers = {};
    });

    it("renders bell button", () => {
        const wrapper = mountBell();
        const btn = wrapper.find("button.relative.rounded-full");
        expect(btn.exists()).toBe(true);
    });

    it("shows unread badge when unreadCount > 0", async () => {
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();
        wrapper.vm.unreadCount = 5;
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("5");
    });

    it("shows 9+ when unreadCount > 9", async () => {
        const wrapper = mountBell();
        wrapper.vm.unreadCount = 12;
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("9+");
    });

    it("opens dropdown on button click", async () => {
        const wrapper = mountBell({ attachTo: document.body });
        await wrapper.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isDropdownOpen).toBe(true);
        expect(document.body.textContent).toContain("Notifications");
        wrapper.unmount();
    });

    it("shows Clear button when dropdown open and notifications exist", async () => {
        global.axios.get = vi.fn().mockResolvedValue({
            data: {
                notifications: [
                    { destination_hash: "h1", display_name: "A", updated_at: new Date().toISOString(), content: "Hi" },
                ],
                unread_count: 1,
            },
        });
        const wrapper = mountBell({ attachTo: document.body });
        await wrapper.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        await new Promise((r) => setTimeout(r, 50));
        expect(document.body.textContent).toContain("Clear");
        wrapper.unmount();
    });

    it("shows No new notifications when empty", async () => {
        const wrapper = mountBell({ attachTo: document.body });
        await wrapper.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        expect(document.body.textContent).toContain("No new notifications");
        wrapper.unmount();
    });

    it("dropdown has Notifications heading when open", async () => {
        const wrapper = mountBell({ attachTo: document.body });
        await wrapper.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        const h3 = document.body.querySelector("h3");
        expect(h3?.textContent).toBe("Notifications");
        wrapper.unmount();
    });
});

describe("NotificationBell websocket reliability", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        wsHandlers = {};
        global.axios.get = vi.fn().mockResolvedValue({ data: { notifications: [], unread_count: 0 } });
        global.axios.post = vi.fn().mockResolvedValue({ data: {} });
    });

    afterEach(() => {
        wsHandlers = {};
    });

    it("reloads on lxmf.delivery websocket event", async () => {
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();

        global.axios.get = vi.fn().mockResolvedValue({
            data: { notifications: [{ destination_hash: "d1", display_name: "X", content: "msg" }], unread_count: 1 },
        });

        simulateWsMessage("lxmf.delivery");
        await new Promise((r) => setTimeout(r, 50));

        expect(wrapper.vm.unreadCount).toBe(1);
    });

    it("reloads on telephone_missed_call websocket event", async () => {
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();

        global.axios.get = vi.fn().mockResolvedValue({
            data: {
                notifications: [
                    {
                        id: 1,
                        type: "telephone_missed_call",
                        destination_hash: "c1",
                        display_name: "Caller",
                        content: "Missed",
                    },
                ],
                unread_count: 1,
            },
        });

        simulateWsMessage("telephone_missed_call", { remote_identity_hash: "c1" });
        await new Promise((r) => setTimeout(r, 50));

        expect(wrapper.vm.unreadCount).toBe(1);
    });

    it("reloads on new_voicemail websocket event", async () => {
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();

        global.axios.get = vi.fn().mockResolvedValue({
            data: {
                notifications: [
                    {
                        id: 2,
                        type: "telephone_voicemail",
                        destination_hash: "v1",
                        display_name: "VM",
                        content: "Voicemail",
                    },
                ],
                unread_count: 1,
            },
        });

        simulateWsMessage("new_voicemail", { remote_identity_hash: "v1" });
        await new Promise((r) => setTimeout(r, 50));

        expect(wrapper.vm.unreadCount).toBe(1);
    });

    it("does NOT reload on unrelated websocket events", async () => {
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();
        const callsBefore = global.axios.get.mock.calls.length;

        simulateWsMessage("telephone_ringing");
        simulateWsMessage("telephone_call_ended");
        simulateWsMessage("lxmf_message_state_updated");
        await new Promise((r) => setTimeout(r, 50));

        expect(global.axios.get.mock.calls.length).toBe(callsBefore);
    });

    it("rapid sequential websocket events all trigger reloads", async () => {
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();
        const initialCalls = global.axios.get.mock.calls.length;

        for (let i = 0; i < 5; i++) {
            simulateWsMessage("lxmf.delivery");
        }
        await new Promise((r) => setTimeout(r, 100));

        expect(global.axios.get.mock.calls.length).toBeGreaterThan(initialCalls);
    });
});

describe("NotificationBell badge accuracy", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        wsHandlers = {};
        global.axios.get = vi.fn().mockResolvedValue({ data: { notifications: [], unread_count: 0 } });
        global.axios.post = vi.fn().mockResolvedValue({ data: {} });
    });

    afterEach(() => {
        wsHandlers = {};
    });

    it("badge hidden when unread count is 0", async () => {
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();
        const badge = wrapper.find("span.bg-red-500");
        expect(badge.exists()).toBe(false);
    });

    it("badge shows exact count for 1-9", async () => {
        for (let n = 1; n <= 9; n++) {
            const wrapper = mountBell();
            wrapper.vm.unreadCount = n;
            await wrapper.vm.$nextTick();
            expect(wrapper.text()).toContain(String(n));
        }
    });

    it("badge shows 9+ for counts above 9", async () => {
        for (const n of [10, 50, 100, 999]) {
            const wrapper = mountBell();
            wrapper.vm.unreadCount = n;
            await wrapper.vm.$nextTick();
            expect(wrapper.text()).toContain("9+");
            expect(wrapper.text()).not.toContain(String(n));
        }
    });

    it("badge updates reactively when unreadCount changes", async () => {
        const wrapper = mountBell();
        wrapper.vm.unreadCount = 3;
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("3");

        wrapper.vm.unreadCount = 0;
        await wrapper.vm.$nextTick();
        expect(wrapper.find("span.bg-red-500").exists()).toBe(false);

        wrapper.vm.unreadCount = 15;
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("9+");
    });

    it("opening dropdown resets unread count to 0", async () => {
        global.axios.get = vi.fn().mockResolvedValue({
            data: { notifications: [{ destination_hash: "d1", display_name: "A", content: "m" }], unread_count: 3 },
        });
        const wrapper = mountBell({ attachTo: document.body });
        wrapper.vm.unreadCount = 3;
        await wrapper.vm.$nextTick();

        await wrapper.find("button").trigger("click");
        await new Promise((r) => setTimeout(r, 50));

        expect(wrapper.vm.unreadCount).toBe(0);
        wrapper.unmount();
    });

    it("API failure does not cause false badge", async () => {
        global.axios.get = vi.fn().mockRejectedValue(new Error("Network error"));
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();
        await new Promise((r) => setTimeout(r, 50));

        expect(wrapper.vm.unreadCount).toBe(0);
        expect(wrapper.vm.notifications).toEqual([]);
    });

    it("API returning null/empty fields does not cause false badge", async () => {
        global.axios.get = vi.fn().mockResolvedValue({ data: { notifications: null, unread_count: null } });
        const wrapper = mountBell();
        await wrapper.vm.$nextTick();
        await new Promise((r) => setTimeout(r, 50));

        expect(wrapper.vm.unreadCount).toBe(0);
    });
});

describe("NotificationBell mark-as-viewed", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        wsHandlers = {};
        global.axios.get = vi.fn().mockResolvedValue({ data: { notifications: [], unread_count: 0 } });
        global.axios.post = vi.fn().mockResolvedValue({ data: {} });
    });

    afterEach(() => {
        wsHandlers = {};
    });

    it("calls mark-as-viewed API when dropdown is opened", async () => {
        global.axios.get = vi.fn().mockResolvedValue({
            data: {
                notifications: [
                    { type: "lxmf_message", destination_hash: "abc", display_name: "A", content: "x" },
                    { type: "telephone_missed_call", id: 42, destination_hash: "mc", display_name: "B", content: "y" },
                ],
                unread_count: 2,
            },
        });
        const wrapper = mountBell({ attachTo: document.body });
        await wrapper.find("button").trigger("click");
        await new Promise((r) => setTimeout(r, 100));

        const postCalls = global.axios.post.mock.calls;
        const markCall = postCalls.find((c) => c[0] === "/api/v1/notifications/mark-as-viewed");
        expect(markCall).toBeTruthy();
        expect(markCall[1].destination_hashes).toContain("abc");
        expect(markCall[1].notification_ids).toContain(42);
        wrapper.unmount();
    });

    it("skips mark-as-viewed when no notifications", async () => {
        const wrapper = mountBell({ attachTo: document.body });
        await wrapper.find("button").trigger("click");
        await new Promise((r) => setTimeout(r, 50));

        const markCalls = global.axios.post.mock.calls.filter((c) => c[0] === "/api/v1/notifications/mark-as-viewed");
        expect(markCalls.length).toBe(0);
        wrapper.unmount();
    });
});

describe("NotificationBell clear all", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        wsHandlers = {};
        global.axios.post = vi.fn().mockResolvedValue({ data: {} });
    });

    afterEach(() => {
        wsHandlers = {};
    });

    it("clears all notifications and marks conversations as read", async () => {
        let callCount = 0;
        global.axios.get = vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/notifications") {
                callCount++;
                if (callCount <= 2) {
                    return Promise.resolve({
                        data: {
                            notifications: [{ destination_hash: "x", display_name: "X", content: "m" }],
                            unread_count: 1,
                        },
                    });
                }
                return Promise.resolve({ data: { notifications: [], unread_count: 0 } });
            }
            if (url === "/api/v1/lxmf/conversations") {
                return Promise.resolve({
                    data: {
                        conversations: [
                            { destination_hash: "conv1", is_unread: true },
                            { destination_hash: "conv2", is_unread: false },
                        ],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountBell({ attachTo: document.body });
        await wrapper.find("button").trigger("click");
        await new Promise((r) => setTimeout(r, 100));

        await wrapper.vm.clearAllNotifications();
        await new Promise((r) => setTimeout(r, 100));

        const readCalls = global.axios.get.mock.calls.filter((c) => c[0]?.includes("/mark-as-read"));
        expect(readCalls.length).toBe(1);
        expect(readCalls[0][0]).toContain("conv1");

        wrapper.unmount();
    });
});
