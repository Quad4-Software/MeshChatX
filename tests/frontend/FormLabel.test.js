import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import FormLabel from "@/components/forms/FormLabel.vue";

describe("FormLabel.vue", () => {
    it("renders slot content", () => {
        const wrapper = mount(FormLabel, {
            slots: {
                default: "Label Text",
            },
        });
        expect(wrapper.text()).toBe("Label Text");
    });

    it("has correct classes", () => {
        const wrapper = mount(FormLabel);
        expect(wrapper.classes()).toContain("block");
        expect(wrapper.classes()).toContain("text-sm");
    });
});
