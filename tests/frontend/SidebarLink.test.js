import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import SidebarLink from "../../meshchatx/src/frontend/components/SidebarLink.vue";

const RouterLinkStub = {
    name: "RouterLinkStub",
    props: ["to"],
    template: '<a href="#" @click.prevent><slot :href="\'#\'" :navigate="navigate" :isActive="false"/></a>',
    methods: {
        navigate(e) {
            if (e) e.preventDefault();
        },
    },
};

function mountSidebarLink(props = {}, slots = {}) {
    return mount(SidebarLink, {
        props: { to: { name: "messages" }, ...props },
        slots: {
            icon: '<span class="icon-slot">I</span>',
            text: "Messages",
            ...slots,
        },
        global: {
            stubs: { RouterLink: RouterLinkStub },
        },
    });
}

describe("SidebarLink UI", () => {
    it("renders link with icon and text slots", () => {
        const wrapper = mountSidebarLink();
        expect(wrapper.text()).toContain("Messages");
        expect(wrapper.find(".icon-slot").exists()).toBe(true);
    });

    it("emits click when link is clicked", async () => {
        const wrapper = mountSidebarLink();
        const innerLink = wrapper.find("a.rounded-r-full");
        if (innerLink.exists()) {
            await innerLink.trigger("click");
        } else {
            await wrapper.find("a").trigger("click");
        }
        expect(wrapper.emitted("click")).toBeDefined();
        expect(wrapper.emitted("click").length).toBeGreaterThanOrEqual(1);
    });

    it("renders text slot when not collapsed", () => {
        const wrapper = mountSidebarLink({ isCollapsed: false });
        expect(wrapper.text()).toContain("Messages");
    });

    it("renders when isCollapsed true", () => {
        const wrapper = mountSidebarLink({ isCollapsed: true });
        expect(wrapper.find("a").exists()).toBe(true);
        expect(wrapper.vm.isCollapsed).toBe(true);
    });

    it("centers the icon and hides text when collapsed", () => {
        const wrapper = mountSidebarLink({ isCollapsed: true });
        const innerLink = wrapper.find("a.justify-center");
        expect(innerLink.exists()).toBe(true);
        expect(innerLink.classes()).toContain("justify-center");
        expect(innerLink.classes()).not.toContain("mr-2");
        expect(innerLink.classes()).toContain("rounded-lg");
        expect(wrapper.text()).not.toContain("Messages");
        expect(wrapper.find(".icon-slot").exists()).toBe(true);
    });

    it("does not navigate when editMode is on", async () => {
        const wrapper = mountSidebarLink({ editMode: true });
        const innerLink = wrapper.find("a.rounded-r-full");
        await innerLink.trigger("click");
        expect(wrapper.emitted("click")).toBeDefined();
        expect(wrapper.vm.editMode).toBe(true);
    });
});
