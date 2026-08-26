// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import AppModal from "@/components/AppModal.vue";

describe("AppModal.vue", () => {
    afterEach(() => {
        document.body.innerHTML = "";
    });

    const mountModal = (props = {}, slots = {}) =>
        mount(AppModal, {
            props: { modelValue: true, title: "Test title", ...props },
            slots,
            global: {
                stubs: {
                    Teleport: { template: '<div class="teleport-stub"><slot /></div>' },
                    MaterialDesignIcon: true,
                },
                mocks: {
                    $t: (key) => key,
                },
            },
        });

    it("renders dialog content when modelValue is true", () => {
        const wrapper = mountModal({}, { default: '<p class="body-slot">Body</p>' });
        expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
        expect(wrapper.text()).toContain("Test title");
        expect(wrapper.find(".body-slot").exists()).toBe(true);
    });

    it("does not render when modelValue is false", () => {
        const wrapper = mountModal({ modelValue: false });
        expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    });

    it("emits update:modelValue false on backdrop click when not persistent", async () => {
        const wrapper = mountModal({ persistent: false });
        const backdrop = wrapper.find(".fixed.inset-0");
        await backdrop.trigger("click");
        expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
        expect(wrapper.emitted("close")).toEqual([[]]);
        wrapper.unmount();
    });

    it("does not close on backdrop click when persistent", async () => {
        const wrapper = mountModal({ persistent: true });
        await wrapper.find(".fixed.inset-0").trigger("click");
        expect(wrapper.emitted("update:modelValue")).toBeUndefined();
        wrapper.unmount();
    });

    it("showClose button emits close events", async () => {
        const wrapper = mountModal({ showClose: true });
        await wrapper.find('button[aria-label="common.close"]').trigger("click");
        expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
        wrapper.unmount();
    });

    it("fullscreen mode sets full viewport panel dimensions", () => {
        const wrapper = mountModal({ fullscreen: true });
        const panel = wrapper.find('[role="dialog"]');
        const style = panel.attributes("style") || "";
        expect(style).toContain("100dvh");
        expect(style).toContain("100vw");
        wrapper.unmount();
    });
});
