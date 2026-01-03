import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NotificationBell from "@/components/NotificationBell.vue";
import { nextTick } from "vue";

describe("NotificationBell.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    notifications: [],
                    unread_count: 0,
                },
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;
    });

    afterEach(() => {
        delete window.axios;
    });

    const mountNotificationBell = () => {
        return mount(NotificationBell, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
                directives: {
                    "click-outside": {},
                },
            },
        });
    };

    it("displays '9+' when unread count is greater than 9", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                notifications: [],
                unread_count: 15,
            },
        });

        const wrapper = mountNotificationBell();
        await nextTick();
        await nextTick();

        expect(wrapper.text()).toContain("9+");
    });

    it("handles long notification names with truncation", async () => {
        const longName = "A".repeat(100);
        axiosMock.get.mockResolvedValue({
            data: {
                notifications: [
                    {
                        type: "lxmf_message",
                        destination_hash: "hash1",
                        display_name: longName,
                        updated_at: new Date().toISOString(),
                        content: "Short content",
                    },
                ],
                unread_count: 1,
            },
        });

        const wrapper = mountNotificationBell();
        await nextTick();

        // Open dropdown
        await wrapper.find("button").trigger("click");
        await nextTick();
        await nextTick();

        const nameElement = wrapper.find(".truncate");
        expect(nameElement.exists()).toBe(true);
        expect(nameElement.text()).toBe(longName);
        expect(nameElement.attributes("title")).toBe(longName);
    });

    it("handles long notification content with line-clamp", async () => {
        const longContent = "B".repeat(500);
        axiosMock.get.mockResolvedValue({
            data: {
                notifications: [
                    {
                        type: "lxmf_message",
                        destination_hash: "hash1",
                        display_name: "User",
                        updated_at: new Date().toISOString(),
                        content: longContent,
                    },
                ],
                unread_count: 1,
            },
        });

        const wrapper = mountNotificationBell();
        await nextTick();

        // Open dropdown
        await wrapper.find("button").trigger("click");
        await nextTick();
        await nextTick();

        const contentElement = wrapper.find(".line-clamp-2");
        expect(contentElement.exists()).toBe(true);
        expect(contentElement.text().trim()).toBe(longContent);
        expect(contentElement.attributes("title")).toBe(longContent);
    });

    it("handles a large number of notifications without crashing", async () => {
        const manyNotifications = Array.from({ length: 50 }, (_, i) => ({
            type: "lxmf_message",
            destination_hash: `hash${i}`,
            display_name: `User ${i}`,
            updated_at: new Date().toISOString(),
            content: `Message ${i}`,
        }));

        axiosMock.get.mockResolvedValue({
            data: {
                notifications: manyNotifications,
                unread_count: 50,
            },
        });

        const wrapper = mountNotificationBell();
        await nextTick();

        // Open dropdown
        await wrapper.find("button").trigger("click");
        await nextTick();
        await nextTick();

        // The buttons are v-for="notification in notifications"
        // Let's find them by class .w-full and hover:bg-gray-50 which are on the same element
        const notificationButtons = wrapper.findAll("div.overflow-y-auto button.w-full");
        expect(notificationButtons.length).toBe(50);
    });

    it("navigates to voicemail tab when voicemail notification is clicked", async () => {
        const routerPush = vi.fn();
        axiosMock.get.mockResolvedValue({
            data: {
                notifications: [
                    {
                        type: "telephone_voicemail",
                        destination_hash: "hash1",
                        display_name: "User",
                        updated_at: new Date().toISOString(),
                        content: "New voicemail",
                    },
                ],
                unread_count: 1,
            },
        });

        const wrapper = mount(NotificationBell, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: { push: routerPush },
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
                directives: {
                    "click-outside": {},
                },
            },
        });

        await nextTick();

        // Click bell to open dropdown
        await wrapper.find("button").trigger("click");
        await nextTick();
        await nextTick();

        // Click it
        const button = wrapper.find("div.overflow-y-auto button.w-full");
        expect(button.exists()).toBe(true);
        await button.trigger("click");

        expect(routerPush).toHaveBeenCalledWith({
            name: "call",
            query: { tab: "voicemail" },
        });
    });
});
