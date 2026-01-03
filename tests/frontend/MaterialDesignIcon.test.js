import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import MaterialDesignIcon from "../../meshchatx/src/frontend/components/MaterialDesignIcon.vue";

describe("MaterialDesignIcon.vue", () => {
    it("converts icon-name to mdiIconName", () => {
        const wrapper = mount(MaterialDesignIcon, {
            props: { iconName: "account-circle" },
        });
        expect(wrapper.vm.mdiIconName).toBe("mdiAccountCircle");
    });

    it("renders svg with correct aria-label", () => {
        const wrapper = mount(MaterialDesignIcon, {
            props: { iconName: "home" },
        });
        expect(wrapper.find("svg").attributes("aria-label")).toBe("home");
    });

    it("falls back to question mark for unknown icons", () => {
        const wrapper = mount(MaterialDesignIcon, {
            props: { iconName: "non-existent-icon" },
        });
        // mdiProgressQuestion should be used
        expect(wrapper.vm.iconPath).not.toBe("");
    });
});
