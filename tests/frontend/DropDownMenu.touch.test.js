import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The real click-outside directive picks touchstart on touch devices. IS_TOUCH
// is resolved when the module loads, so the window flag must be set before the
// dynamic imports below.
describe("DropDownMenu touch handling", () => {
    let DropDownMenu;
    let clickOutsideDirective;
    let wrapper;

    beforeEach(async () => {
        vi.resetModules();
        window.ontouchstart = null;
        ({ default: DropDownMenu } = await import("../../meshchatx/src/frontend/components/DropDownMenu.vue"));
        ({ clickOutsideDirective } = await import("../../meshchatx/src/frontend/libs/clickOutside.js"));
        document.body.innerHTML = "";
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.unmount();
            wrapper = null;
        }
        delete window.ontouchstart;
        document.body.innerHTML = "";
    });

    async function openMenu() {
        wrapper = mount(DropDownMenu, {
            attachTo: document.body,
            slots: {
                button: '<button type="button" class="menu-button">Menu</button>',
                items: '<div class="menu-item">Item 1</div>',
            },
            global: {
                directives: { "click-outside": clickOutsideDirective },
            },
        });
        await wrapper.find("button").trigger("click");
        // Let the positioning nextTicks and the directive's deferred listener
        // attachment settle.
        await new Promise((resolve) => setTimeout(resolve, 0));
        await wrapper.vm.$nextTick();
    }

    function menuItem() {
        return document.body.querySelector(".menu-item");
    }

    it("touch on a teleported menu item does not close the menu before click", async () => {
        await openMenu();
        expect(wrapper.vm.isShowingMenu).toBe(true);
        const item = menuItem();
        expect(item).toBeTruthy();

        item.dispatchEvent(new Event("touchstart", { bubbles: true, composed: true }));
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isShowingMenu).toBe(true);

        const onItemClick = vi.fn();
        item.addEventListener("click", onItemClick);
        item.dispatchEvent(new Event("click", { bubbles: true, composed: true }));
        await wrapper.vm.$nextTick();
        expect(onItemClick).toHaveBeenCalled();
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });

    it("touch outside the wrapper and the panel closes the menu", async () => {
        await openMenu();
        document.body.dispatchEvent(new Event("touchstart", { bubbles: true, composed: true }));
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });

    it("touch on the button area does not close the menu", async () => {
        await openMenu();
        const button = wrapper.find("button").element;
        button.dispatchEvent(new Event("touchstart", { bubbles: true, composed: true }));
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isShowingMenu).toBe(true);
    });
});
