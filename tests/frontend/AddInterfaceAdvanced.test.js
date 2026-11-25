// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AddInterfacePage from "../../meshchatx/src/frontend/components/interfaces/AddInterfacePage.vue";
import BitrateInput from "../../meshchatx/src/frontend/components/forms/BitrateInput.vue";
import DurationInput from "../../meshchatx/src/frontend/components/forms/DurationInput.vue";

const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
};
window.api = mockAxios;

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

const mountPage = () =>
    mount(AddInterfacePage, {
        global: {
            mocks: {
                $route: { query: {} },
                $router: { push: vi.fn() },
                $t: (msg) => msg,
            },
            stubs: ["RouterLink", "MaterialDesignIcon"],
        },
    });

describe("AddInterfacePage.vue advanced sections", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAxios.get.mockResolvedValue({ data: {} });
        mockAxios.post.mockResolvedValue({ data: { message: "ok" } });
    });

    async function expandFirstAdvancedSection(wrapper) {
        const titleSpan = wrapper.findAll("span").find((s) => s.text().includes("interfaces.advanced"));
        expect(titleSpan, "advanced section title present").toBeDefined();
        // the clickable header is the title row inside ExpandingSection
        const header = titleSpan.element.closest("div.flex.p-2");
        expect(header).not.toBeNull();
        header.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await wrapper.vm.$nextTick();
    }

    it("keeps TCP client advanced fields collapsed by default", async () => {
        const wrapper = mountPage();
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).not.toContain("Use KISS framing (legacy compatibility)");
        // core fields stay visible without expanding
        expect(wrapper.text()).toContain("Target Host");
        expect(wrapper.text()).toContain("interfaces.discovery_default_bootstrap_only");
    });

    it("reveals advanced fields after expanding and keeps bindings", async () => {
        const wrapper = mountPage();
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        await wrapper.vm.$nextTick();

        await expandFirstAdvancedSection(wrapper);
        expect(wrapper.text()).toContain("Use KISS framing (legacy compatibility)");
        expect(wrapper.text()).toContain("Max Reconnect Tries");

        // binding still flows into the same vm state the payload builder reads
        wrapper.vm.newInterfaceKISSFramingEnabled = true;
        await wrapper.vm.$nextTick();
        wrapper.vm.newInterfaceName = "x";
        wrapper.vm.newInterfaceTargetHost = "example.com";
        wrapper.vm.newInterfaceTargetPort = "4242";
        await wrapper.vm.saveInterface();
        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({ kiss_framing: true })
        );
    });

    it("hides AutoInterface low-level options behind advanced", async () => {
        const wrapper = mountPage();
        wrapper.vm.newInterfaceType = "AutoInterface";
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).not.toContain("Discovery Scope");
        expect(wrapper.text()).not.toContain("Configured Bitrate");
        expect(wrapper.text()).toContain("Group ID (optional)");

        await expandFirstAdvancedSection(wrapper);
        expect(wrapper.text()).toContain("Discovery Scope");
        expect(wrapper.text()).toContain("Configured Bitrate");
    });

    it("hides HTTP tunnel low-level options behind advanced", async () => {
        const wrapper = mountPage();
        wrapper.vm.newInterfaceType = "HTTPInterface";
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("interfaces.http_tunnel_server_url");
        expect(wrapper.text()).not.toContain("interfaces.http_tunnel_poll_interval");
        expect(wrapper.text()).not.toContain("interfaces.http_tunnel_user_agent");

        await expandFirstAdvancedSection(wrapper);
        expect(wrapper.text()).toContain("interfaces.http_tunnel_poll_interval");
        expect(wrapper.text()).toContain("interfaces.http_tunnel_user_agent");
    });
});

describe("BitrateInput", () => {
    it("presents raw bps in human units", async () => {
        const wrapper = mount(BitrateInput, {
            props: { modelValue: 20000 },
        });
        const input = wrapper.find("input");
        const select = wrapper.find("select");
        expect(input.element.value).toBe("20");
        expect(select.element.value).toBe("kbps");
    });

    it("emits raw bps when the user types", async () => {
        const wrapper = mount(BitrateInput, {
            props: { modelValue: null },
        });
        await wrapper.find("input").setValue(20);
        expect(wrapper.emitted("update:modelValue")).toEqual([[20000]]);
    });

    it("emits converted raw bps for larger units", async () => {
        const wrapper = mount(BitrateInput, {
            props: { modelValue: null },
        });
        await wrapper.find("select").setValue("Mbps");
        await wrapper.find("input").setValue(5);
        expect(wrapper.emitted("update:modelValue")).toEqual([[5000000]]);
    });

    it("emits null when cleared", async () => {
        const wrapper = mount(BitrateInput, {
            props: { modelValue: 20000 },
        });
        await wrapper.find("input").setValue("");
        expect(wrapper.emitted("update:modelValue")).toEqual([[null]]);
    });

    it("rescales the display when switching units without changing the raw value", async () => {
        const wrapper = mount(BitrateInput, {
            props: { modelValue: 20000 },
        });
        await wrapper.find("select").setValue("bps");
        expect(wrapper.find("input").element.value).toBe("20000");
        expect(wrapper.emitted("update:modelValue") || []).toEqual([]);
    });
});

describe("DurationInput", () => {
    it("presents whole-minute seconds as minutes", () => {
        const wrapper = mount(DurationInput, {
            props: { modelValue: 600 },
        });
        expect(wrapper.find("input").element.value).toBe("10");
        expect(wrapper.find("select").element.value).toBe("minutes");
    });

    it("keeps odd values in seconds", () => {
        const wrapper = mount(DurationInput, {
            props: { modelValue: 90 },
        });
        expect(wrapper.find("input").element.value).toBe("90");
        expect(wrapper.find("select").element.value).toBe("seconds");
    });

    it("emits raw seconds when the user types", async () => {
        const wrapper = mount(DurationInput, {
            props: { modelValue: null },
        });
        await wrapper.find("select").setValue("minutes");
        await wrapper.find("input").setValue(10);
        expect(wrapper.emitted("update:modelValue")).toEqual([[600]]);
    });

    it("emits null when cleared", async () => {
        const wrapper = mount(DurationInput, {
            props: { modelValue: 600 },
        });
        await wrapper.find("input").setValue("");
        expect(wrapper.emitted("update:modelValue")).toEqual([[null]]);
    });
});
