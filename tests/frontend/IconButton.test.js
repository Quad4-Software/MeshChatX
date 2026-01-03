import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import IconButton from "../../meshchatx/src/frontend/components/IconButton.vue";

describe("IconButton.vue", () => {
    it("renders slot content", () => {
        const wrapper = mount(IconButton, {
            slots: {
                default: '<span class="test-icon">icon</span>',
            },
        });
        expect(wrapper.find(".test-icon").exists()).toBe(true);
        expect(wrapper.text()).toBe("icon");
    });

    it("has correct button type", () => {
        const wrapper = mount(IconButton);
        expect(wrapper.attributes("type")).toBe("button");
    });
});
