import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Interface from "../../meshchatx/src/frontend/components/interfaces/Interface.vue";

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: { alert: vi.fn() },
}));

const defaultIface = {
    _name: "Default Interface",
    type: "AutoInterface",
    enabled: true,
    discoverable: true,
};

function mountInterface(props = {}, options = {}) {
    return mount(Interface, {
        props: { iface: { ...defaultIface, ...props }, isReticulumRunning: true },
        global: {
            mocks: { $t: (key) => key },
            stubs: ["MaterialDesignIcon", "IconButton", "DropDownMenu", "DropDownMenuItem"],
        },
        ...options,
    });
}

describe("Interface.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders interface name and type", () => {
        const wrapper = mountInterface();
        expect(wrapper.text()).toContain("Default Interface");
        expect(wrapper.text()).toContain("AutoInterface");
    });

    it("emits disable when Disable button is clicked", async () => {
        const wrapper = mountInterface();
        const disableBtn = wrapper.find("button.secondary-chip");
        await disableBtn.trigger("click");
        expect(wrapper.emitted("disable")).toHaveLength(1);
    });

    it("emits enable when Enable button is clicked for disabled interface", async () => {
        const wrapper = mountInterface({ enabled: false });
        const enableBtn = wrapper.find("button.primary-chip");
        await enableBtn.trigger("click");
        expect(wrapper.emitted("enable")).toHaveLength(1);
    });

    it("has overflow containment classes on card and content", () => {
        const wrapper = mountInterface();
        const card = wrapper.find(".interface-card");
        expect(card.classes()).toContain("min-w-0");
        const contentArea = wrapper.find(".min-w-0.overflow-hidden");
        expect(contentArea.exists()).toBe(true);
    });

    it("has break-words on description for long host:port", () => {
        const wrapper = mountInterface({
            _name: "RNS Testnet Amsterdam",
            type: "TCPClientInterface",
            target_host: "amsterdam.connect.reticulum.network",
            target_port: 4965,
        });
        const desc = wrapper.find(".text-sm.text-gray-600");
        expect(desc.classes()).toContain("break-words");
        expect(desc.classes()).toContain("min-w-0");
    });

    it("has responsive layout classes for stacking on small screens", () => {
        const wrapper = mountInterface();
        const outer = wrapper.find(".flex.flex-col.sm\\:flex-row");
        expect(outer.exists()).toBe(true);
    });

    it("renders without overflow when given very long name and description", () => {
        const longName = "A".repeat(120);
        const wrapper = mountInterface({
            _name: longName,
            type: "TCPClientInterface",
            target_host: "very-long-hostname-that-could-overflow-on-mobile.example.reticulum.network",
            target_port: 4242,
        });
        const card = wrapper.find(".interface-card");
        expect(card.exists()).toBe(true);
        const contentWrapper = wrapper.find(".flex-1.min-w-0.space-y-2");
        expect(contentWrapper.exists()).toBe(true);
        const nameEl = wrapper.find(".truncate.min-w-0");
        expect(nameEl.exists()).toBe(true);
    });

    it("action buttons and dropdown have shrink-0 to prevent squashing", () => {
        const wrapper = mountInterface();
        const actionsCol = wrapper.find(".flex.flex-col.sm\\:flex-row.gap-2");
        expect(actionsCol.classes()).toContain("sm:shrink-0");
        const btn = wrapper.find("button.secondary-chip");
        expect(btn.classes()).toContain("shrink-0");
    });

    it("detail-value has break-all for long addresses", () => {
        const wrapper = mountInterface({
            _name: "UDP Test",
            type: "UDPInterface",
            listen_ip: "0.0.0.0",
            listen_port: 4242,
            forward_ip: "192.168.1.100",
            forward_port: 4242,
        });
        const detailValues = wrapper.findAll(".detail-value");
        expect(detailValues.length).toBeGreaterThan(0);
        detailValues.forEach((el) => {
            expect(el.classes()).toContain("break-all");
            expect(el.classes()).toContain("min-w-0");
        });
    });
});

describe("Interface.vue overflow at different viewports", () => {
    it("card has min-w-0 so it can shrink in grid", () => {
        const wrapper = mountInterface();
        expect(wrapper.find(".interface-card").classes()).toContain("min-w-0");
    });

    it("icon and chips have shrink-0 so they do not collapse", () => {
        const wrapper = mountInterface();
        expect(wrapper.find(".interface-card__icon").classes()).toContain("shrink-0");
        expect(wrapper.find(".type-chip").classes()).toContain("shrink-0");
    });
});
