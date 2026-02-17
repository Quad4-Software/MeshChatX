import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import NotificationBell from "../../meshchatx/src/frontend/components/NotificationBell.vue";

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: { on: vi.fn(), off: vi.fn() },
}));

vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: { formatTimeAgo: (d) => "1h ago" },
}));

const MaterialDesignIcon = { template: "<div class=\"mdi\"></div>", props: ["iconName"] };

function mountBell(options = {}) {
    return mount(NotificationBell, {
        global: {
            components: { MaterialDesignIcon },
            directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
        },
        ...options,
    });
}

describe("NotificationBell UI", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        global.axios.get = vi.fn().mockResolvedValue({ data: { notifications: [], unread_count: 0 } });
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
