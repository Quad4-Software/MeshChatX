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
                preferredRenderer: "auto",
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

    it("shows engine select and FPS", () => {
        const wrapper = mountToolbar();
        const select = wrapper.find("#visualiser-engine-select");
        expect(select.exists()).toBe(true);
        expect(select.element.value).toBe("auto");
        expect(wrapper.text()).toContain("58");
        expect(wrapper.text()).toContain("visualiser.fps");
        expect(wrapper.text()).toContain("visualiser.renderer_option_webgl");
        expect(wrapper.text()).toContain("visualiser.renderer_option_vis");
    });

    it("emits preferred renderer when engine select changes", async () => {
        const wrapper = mountToolbar({ preferredRenderer: "auto", engineMode: "webgl" });
        const select = wrapper.find("#visualiser-engine-select");
        await select.setValue("webgl");
        expect(wrapper.emitted("update:preferredRenderer")?.[0]).toEqual(["webgl"]);
        await select.setValue("vis");
        expect(wrapper.emitted("update:preferredRenderer")?.[1]).toEqual(["vis"]);
    });

    it("styles select from active engine mode", () => {
        const webgl = mountToolbar({ engineMode: "webgl", preferredRenderer: "webgl", fps: 60 });
        expect(webgl.find("#visualiser-engine-select").classes().join(" ")).toContain("text-sky-600");

        const fallback = mountToolbar({ engineMode: "fallback", preferredRenderer: "vis", fps: 0 });
        expect(fallback.find("#visualiser-engine-select").classes().join(" ")).toContain("text-amber-600");
        expect(fallback.text()).toContain("--");
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
