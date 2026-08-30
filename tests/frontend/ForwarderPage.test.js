import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ForwarderPage from "@/components/forwarder/ForwarderPage.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import ToastUtils from "@/js/ToastUtils";
import DialogUtils from "@/js/DialogUtils";

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        send: vi.fn(() => true),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
    },
}));

describe("ForwarderPage.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        WebSocketConnection.send.mockReturnValue(true);
    });

    const mountForwarderPage = () => {
        return mount(ForwarderPage, {
            global: {
                mocks: {
                    $t: (key, params) => key + (params ? JSON.stringify(params) : ""),
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                },
            },
        });
    };

    it("renders the forwarder page", () => {
        const wrapper = mountForwarderPage();
        expect(wrapper.text()).toContain("forwarder.title");
        expect(wrapper.text()).toContain("forwarder.add_rule");
    });

    it("fetches rules on mount", () => {
        mountForwarderPage();
        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxmf.forwarding.rules.get",
            })
        );
    });

    it("adds a new rule", async () => {
        const wrapper = mountForwarderPage();
        await wrapper.setData({
            newRule: {
                name: "Test Rule",
                forward_to_hash: "a".repeat(32),
                source_filter_hash: "",
                is_active: true,
            },
        });

        const addButton = wrapper.find("button[class*='bg-blue-600']");
        await addButton.trigger("click");

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxmf.forwarding.rule.add",
                rule: {
                    name: "Test Rule",
                    forward_to_hash: "a".repeat(32),
                    source_filter_hash: "",
                    is_active: true,
                },
            })
        );
    });

    it("handles incoming rules from websocket", async () => {
        const wrapper = mountForwarderPage();
        await wrapper.vm.onForwardingRules({
            type: "lxmf.forwarding.rules",
            rules: [{ id: "rule1", name: "Rule 1", forward_to_hash: "hash1", is_active: true }],
        });

        expect(wrapper.vm.rules.length).toBe(1);
        expect(wrapper.text()).toContain("Rule 1");
    });

    it("toggles a rule", async () => {
        const wrapper = mountForwarderPage();
        await wrapper.setData({
            rules: [{ id: "rule1", name: "Rule 1", forward_to_hash: "hash1", is_active: true }],
        });

        const toggleButton = wrapper.find("button[title='forwarder.disabled']");
        await toggleButton.trigger("click");

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxmf.forwarding.rule.toggle",
                id: "rule1",
            })
        );
    });

    it("rejects a non-hex destination hash", async () => {
        const wrapper = mountForwarderPage();
        await wrapper.setData({
            newRule: {
                name: "bad",
                forward_to_hash: "not-a-hash",
                source_filter_hash: "",
                is_active: true,
            },
        });
        await wrapper.find("button[class*='bg-blue-600']").trigger("click");
        expect(ToastUtils.warning).toHaveBeenCalled();
        const addCalls = WebSocketConnection.send.mock.calls.filter((call) =>
            String(call[0]).includes("lxmf.forwarding.rule.add")
        );
        expect(addCalls).toHaveLength(0);
    });

    it("deletes a rule after confirm", async () => {
        const wrapper = mountForwarderPage();
        await wrapper.setData({
            rules: [{ id: "rule1", name: "Rule 1", forward_to_hash: "a".repeat(32), is_active: true }],
        });
        await wrapper.vm.deleteRule("rule1");
        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxmf.forwarding.rule.delete",
                id: "rule1",
            })
        );
        expect(ToastUtils.success).toHaveBeenCalled();
    });
});
