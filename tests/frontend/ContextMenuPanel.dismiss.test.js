import { describe, it, expect, vi, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import ContextMenuPanel from "@/components/contextmenu/ContextMenuPanel.vue";
import clickOutsidePlugin from "@/libs/clickOutside.js";

// Regression: ContextMenuPanel originally had a fragment root (panel + caret),
// and Vue silently ignores runtime directives on non-element roots. Every
// v-click-outside placed on <ContextMenuPanel> was dead code, so outside
// clicks and repeated right-clicks never dismissed the menus. The panel now
// has a single display:contents wrapper so the directive binds a real element.

function mountMenu() {
    return mount(
        {
            components: { ContextMenuPanel },
            data: () => ({ show: false, hits: 0 }),
            template: `
                <div>
                    <ContextMenuPanel
                        v-click-outside="{ handler: () => hits++, capture: true }"
                        :show="show"
                        :x="10"
                        :y="10"
                    ><button class="item">x</button></ContextMenuPanel>
                    <button class="other">y</button>
                </div>`,
        },
        { attachTo: document.body, global: { plugins: [clickOutsidePlugin] } }
    );
}

describe("ContextMenuPanel dismissal", () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it("component root is a single element so directives bind", async () => {
        const wrapper = mountMenu();
        const el = wrapper.findComponent(ContextMenuPanel).element;
        expect(el.nodeType).toBe(Node.ELEMENT_NODE);
        wrapper.unmount();
    });

    it("outside contextmenu dismisses; inside does not; re-render does not duplicate", async () => {
        vi.useFakeTimers();
        const wrapper = mountMenu();
        wrapper.vm.show = true;
        await wrapper.vm.$nextTick();
        vi.runAllTimers();
        await wrapper.vm.$nextTick();

        const panel = document.querySelector(".context-menu-panel");
        const other = document.querySelector(".other");
        expect(panel).toBeTruthy();

        panel.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true }));
        expect(wrapper.vm.hits).toBe(0);

        other.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true }));
        expect(wrapper.vm.hits).toBe(1);

        other.dispatchEvent(new MouseEvent("touchstart", { bubbles: true }));
        expect(wrapper.vm.hits).toBe(2);

        // Re-render swaps the binding object identity. Listeners must not stack.
        wrapper.vm.show = false;
        await wrapper.vm.$nextTick();
        wrapper.vm.show = true;
        await wrapper.vm.$nextTick();
        vi.runAllTimers();
        await wrapper.vm.$nextTick();

        other.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true }));
        expect(wrapper.vm.hits).toBe(3);

        wrapper.unmount();
        other.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true }));
        expect(wrapper.vm.hits).toBe(3);
    });
});
