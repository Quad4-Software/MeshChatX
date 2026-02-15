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
        expect(wrapper.vm.iconPath).not.toBe("");
    });

    it("renders an svg element for valid icon", () => {
        const wrapper = mount(MaterialDesignIcon, {
            props: { iconName: "home" },
        });
        expect(wrapper.find("svg").exists()).toBe(true);
    });

    it("accepts iconName prop", () => {
        const wrapper = mount(MaterialDesignIcon, {
            props: { iconName: "cog" },
        });
        expect(wrapper.props("iconName")).toBe("cog");
    });
});
