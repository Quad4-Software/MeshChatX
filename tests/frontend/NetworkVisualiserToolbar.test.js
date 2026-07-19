import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, afterEach } from "vitest";
import NetworkVisualiserToolbar from "@/components/network-visualiser/internal/NetworkVisualiserToolbar.vue";

describe("NetworkVisualiserToolbar", () => {
    let wrapper;

    afterEach(() => {
        wrapper?.unmount();
        wrapper = null;
    });

    const mountToolbar = (props = {}) => {
        wrapper = mount(NetworkVisualiserToolbar, {
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
                    Teleport: true,
                    MaterialDesignIcon: {
                        props: ["iconName"],
                        template: `<span class="mdi-stub" :data-icon="iconName"></span>`,
                    },
                },
                directives: {
                    "click-outside": {
                        mounted() {},
                        unmounted() {},
                    },
                },
            },
            attachTo: document.body,
        });
        return wrapper;
    };

    it("keeps the control panel at a fixed sm width class", () => {
        const w = mountToolbar();
        const panel = w.find(".pointer-events-auto.border");
        expect(panel.classes()).toContain("sm:w-[280px]");
        expect(panel.classes()).toContain("sm:max-w-[280px]");
        expect(panel.classes()).not.toContain("sm:w-auto");
        expect(panel.classes()).not.toContain("sm:min-w-[280px]");
    });

    it("shows themed engine trigger and FPS without a native select", () => {
        const w = mountToolbar();
        expect(w.find("select").exists()).toBe(false);
        const trigger = w.find("#visualiser-engine-select");
        expect(trigger.exists()).toBe(true);
        expect(trigger.element.tagName).toBe("BUTTON");
        expect(trigger.text()).toContain("visualiser.renderer_option_auto_short");
        expect(w.text()).toContain("58");
        expect(w.text()).toContain("visualiser.fps");
    });

    it("opens custom engine menu and emits preferred renderer", async () => {
        const w = mountToolbar({ preferredRenderer: "auto", engineMode: "webgl" });
        await w.find("#visualiser-engine-select").trigger("click");
        await flushPromises();
        expect(w.find('[role="listbox"]').exists()).toBe(true);
        expect(w.text()).toContain("visualiser.renderer_option_webgl");
        expect(w.text()).toContain("visualiser.renderer_option_vis");

        const options = w.findAll('[role="option"]');
        expect(options.length).toBe(3);
        await options[1].trigger("click");
        expect(w.emitted("update:preferredRenderer")?.[0]).toEqual(["webgl"]);
        expect(w.find('[role="listbox"]').exists()).toBe(false);
    });

    it("styles trigger from active engine mode", () => {
        const webgl = mountToolbar({ engineMode: "webgl", preferredRenderer: "webgl", fps: 60 });
        expect(webgl.find("#visualiser-engine-select").classes().join(" ")).toContain("text-sky-600");
        expect(webgl.find("#visualiser-engine-select").text()).toContain("visualiser.renderer_option_webgl_short");
        webgl.unmount();

        const fallback = mountToolbar({ engineMode: "fallback", preferredRenderer: "vis", fps: 0 });
        expect(fallback.find("#visualiser-engine-select").classes().join(" ")).toContain("text-amber-600");
        expect(fallback.find("#visualiser-engine-select").text()).toContain("visualiser.renderer_option_vis_short");
        expect(fallback.text()).toContain("--");
    });

    it("uses MDI magnify for search and refresh for update button", () => {
        const w = mountToolbar({ isUpdating: false, isLoading: false });
        const icons = w.findAll(".mdi-stub").map((n) => n.attributes("data-icon"));
        expect(icons).toContain("magnify");
        expect(icons).toContain("refresh");
        expect(icons).not.toContain(undefined);
    });

    it("uses loading icon only for manual loading, not auto-update busy", () => {
        const autoBusy = mountToolbar({ isUpdating: true, isLoading: false });
        const autoIcons = autoBusy.findAll(".mdi-stub").map((n) => n.attributes("data-icon"));
        expect(autoIcons).toContain("refresh");
        expect(autoIcons).not.toContain("loading");
        autoBusy.unmount();

        const manualBusy = mountToolbar({ isUpdating: true, isLoading: true });
        const manualIcons = manualBusy.findAll(".mdi-stub").map((n) => n.attributes("data-icon"));
        expect(manualIcons).toContain("loading");
    });
});
