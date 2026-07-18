import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import NetworkVisualiserToolbar from "@/components/network-visualiser/internal/NetworkVisualiserToolbar.vue";

describe("NetworkVisualiserToolbar", () => {
    const mountToolbar = (props = {}) =>
        mount(NetworkVisualiserToolbar, {
            props: {
                isShowingControls: true,
                nodeCount: 12,
                edgeCount: 8,
                onlineInterfaceCount: 2,
                offlineInterfaceCount: 1,
                engineMode: "wasm",
                fps: 58,
                ...props,
            },
            global: {
                mocks: { $t: (k, v) => (v ? `${k}:${JSON.stringify(v)}` : k) },
                stubs: {
                    Toggle: true,
                    MaterialDesignIcon: {
                        props: ["iconName"],
                        template: `<span class="mdi-stub" :data-icon="iconName"></span>`,
                    },
                },
            },
        });

    it("shows WASM engine label and FPS", () => {
        const wrapper = mountToolbar();
        expect(wrapper.text()).toContain("visualiser.engine_wasm");
        expect(wrapper.text()).toContain("58");
        expect(wrapper.text()).toContain("visualiser.fps");
    });

    it("shows JS fallback engine label", () => {
        const wrapper = mountToolbar({ engineMode: "fallback", fps: 0 });
        expect(wrapper.text()).toContain("visualiser.engine_fallback");
        expect(wrapper.text()).toContain("--");
    });

    it("shows WebGL engine label", () => {
        const wrapper = mountToolbar({ engineMode: "webgl", fps: 60 });
        expect(wrapper.text()).toContain("visualiser.engine_webgl");
        expect(wrapper.text()).toContain("60");
    });

    it("uses MDI magnify for search and refresh for update button", () => {
        const wrapper = mountToolbar({ isUpdating: false, isLoading: false });
        const icons = wrapper.findAll(".mdi-stub").map((n) => n.attributes("data-icon"));
        expect(icons).toContain("magnify");
        expect(icons).toContain("refresh");
        expect(icons).not.toContain(undefined);
    });

    it("uses loading icon only for manual loading, not auto-update busy", () => {
        const autoBusy = mountToolbar({ isUpdating: true, isLoading: false });
        const autoIcons = autoBusy.findAll(".mdi-stub").map((n) => n.attributes("data-icon"));
        expect(autoIcons).toContain("refresh");
        expect(autoIcons).not.toContain("loading");

        const manualBusy = mountToolbar({ isUpdating: true, isLoading: true });
        const manualIcons = manualBusy.findAll(".mdi-stub").map((n) => n.attributes("data-icon"));
        expect(manualIcons).toContain("loading");
    });
});
