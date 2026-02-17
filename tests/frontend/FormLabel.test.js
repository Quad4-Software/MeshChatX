import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import FormLabel from "../../meshchatx/src/frontend/components/forms/FormLabel.vue";

describe("FormLabel UI", () => {
    it("renders label with slot content", () => {
        const wrapper = mount(FormLabel, {
            slots: { default: "Username" },
        });
        expect(wrapper.find("label").exists()).toBe(true);
        expect(wrapper.text()).toContain("Username");
    });

    it("has label classes", () => {
        const wrapper = mount(FormLabel, { slots: { default: "X" } });
        expect(wrapper.find("label").classes()).toContain("block");
        expect(wrapper.find("label").classes()).toContain("text-sm");
    });
});
