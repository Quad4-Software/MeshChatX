// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import IntegrityWarningModal from "@/components/IntegrityWarningModal.vue";
import AppUpdatePrompt from "@/components/AppUpdatePrompt.vue";

describe("Vuetify migration modal smoke", () => {
    const modalMountOptions = {
        global: {
            stubs: {
                AppModal: false,
                Teleport: { template: '<div class="teleport-stub"><slot /></div>' },
                MaterialDesignIcon: true,
            },
            mocks: { $t: (key) => key },
        },
    };

    it("IntegrityWarningModal mounts with AppModal and no v-dialog", async () => {
        window.api = { post: vi.fn().mockResolvedValue({}) };
        const wrapper = mount(IntegrityWarningModal, modalMountOptions);
        wrapper.vm.visible = true;
        await wrapper.vm.$nextTick();
        expect(wrapper.html()).not.toContain("v-dialog");
        expect(wrapper.findComponent({ name: "AppModal" }).exists()).toBe(true);
        wrapper.unmount();
    });

    it("AppUpdatePrompt mounts with AppModal shell", () => {
        const wrapper = mount(AppUpdatePrompt, {
            ...modalMountOptions,
            props: {
                modelValue: true,
                title: "Update",
                description: "A new version is available.",
                primaryLabel: "Download",
            },
        });
        expect(wrapper.findComponent({ name: "AppModal" }).exists()).toBe(true);
        expect(wrapper.text()).toContain("Update");
        expect(wrapper.text()).toContain("A new version is available.");
        wrapper.unmount();
    });
});
