// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import SidebarVirtualList from "@/components/SidebarVirtualList.vue";

function makeItems(count) {
    return Array.from({ length: count }, (_v, index) => ({
        destination_hash: `hash-${index}`,
        display_name: `Peer ${index}`,
    }));
}

describe("SidebarVirtualList.vue", () => {
    it("renders all rows when virtualize is false", () => {
        const items = makeItems(5);
        const wrapper = mount(SidebarVirtualList, {
            props: { items, virtualize: false },
            slots: {
                item: `<div class="row">{{ item.display_name }}</div>`,
            },
        });
        expect(wrapper.findAll(".row")).toHaveLength(5);
        expect(wrapper.text()).toContain("Peer 4");
    });

    it("virtualizes long lists and uses a spacer container", () => {
        const items = makeItems(80);
        const wrapper = mount(SidebarVirtualList, {
            props: { items, virtualize: true },
            slots: {
                item: `<div class="row">{{ item.display_name }}</div>`,
            },
        });
        expect(wrapper.find(".relative.w-full").exists()).toBe(true);
        const style = wrapper.find(".relative.w-full").attributes("style") || "";
        expect(style).toContain("height:");
    });

    it("forwards scroll events to parent handlers", async () => {
        const items = makeItems(3);
        const wrapper = mount(SidebarVirtualList, {
            props: { items, virtualize: false },
            slots: {
                item: `<div class="row">{{ item.display_name }}</div>`,
            },
        });
        await wrapper.trigger("scroll");
        expect(wrapper.emitted("scroll")).toHaveLength(1);
    });
});
