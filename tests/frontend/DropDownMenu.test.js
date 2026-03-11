import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import DropDownMenu from "../../meshchatx/src/frontend/components/DropDownMenu.vue";

function mountDropDown(slots = {}) {
    return mount(DropDownMenu, {
        slots: {
            button: '<button type="button">Menu</button>',
            items: '<div class="menu-item">Item 1</div>',
            ...slots,
        },
        global: {
            directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
        },
    });
}

describe("DropDownMenu UI", () => {
    it("renders button slot", () => {
        const wrapper = mountDropDown();
        expect(wrapper.text()).toContain("Menu");
    });

    it("shows menu when button clicked", async () => {
        const wrapper = mountDropDown();
        expect(wrapper.vm.isShowingMenu).toBe(false);
        await wrapper.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isShowingMenu).toBe(true);
        const menuContent = document.body.querySelector(".menu-item");
        expect(menuContent).toBeTruthy();
        expect(menuContent.textContent).toContain("Item 1");
    });

    it("hides menu when button clicked again", async () => {
        const wrapper = mountDropDown();
        await wrapper.find("button").trigger("click");
        expect(wrapper.vm.isShowingMenu).toBe(true);
        await wrapper.find("button").trigger("click");
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });

    it("renders items slot when open", async () => {
        const wrapper = mountDropDown({ items: '<div class="custom-item">Custom</div>' });
        await wrapper.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        const menuContent = document.body.querySelector(".custom-item");
        expect(menuContent).toBeTruthy();
        expect(menuContent.textContent).toContain("Custom");
    });
});
