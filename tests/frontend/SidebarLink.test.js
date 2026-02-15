import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import SidebarLink from "@/components/SidebarLink.vue";

describe("SidebarLink.vue", () => {
    const defaultProps = {
        to: { name: "test-route" },
        isCollapsed: false,
    };

    const RouterLinkStub = {
        template: '<slot :href="\'/test\'" :navigate="navigate || (() => {})" :isActive="isActive || false" />',
        props: ["to", "custom", "navigate", "isActive"],
    };

    it("renders icon and text slots", () => {
        const wrapper = mount(SidebarLink, {
            props: defaultProps,
            slots: {
                icon: '<span class="icon">icon</span>',
                text: '<span class="text">Link Text</span>',
            },
            global: {
                stubs: {
                    RouterLink: RouterLinkStub,
                },
            },
        });
        expect(wrapper.find(".icon").exists()).toBe(true);
        expect(wrapper.find(".text").exists()).toBe(true);
        expect(wrapper.text()).toContain("Link Text");
    });

    it("applies collapsed class when isCollapsed is true", () => {
        const wrapper = mount(SidebarLink, {
            props: { ...defaultProps, isCollapsed: true },
            slots: {
                icon: '<span class="icon">icon</span>',
                text: '<span class="text">Link Text</span>',
            },
            global: {
                stubs: {
                    RouterLink: RouterLinkStub,
                },
            },
        });
        // v-if="!isCollapsed" means the span with the text won't exist
        expect(wrapper.find(".text").exists()).toBe(false);
    });

    it("emits click event and calls navigate when clicked", async () => {
        const navigate = vi.fn();
        const wrapper = mount(SidebarLink, {
            props: defaultProps,
            global: {
                stubs: {
                    RouterLink: {
                        template: '<slot :href="\'/test\'" :navigate="navigate" :isActive="false" />',
                        props: ["to", "custom"],
                        setup() {
                            return { navigate };
                        },
                    },
                },
            },
        });

        await wrapper.find("a").trigger("click");
        expect(wrapper.emitted("click")).toBeTruthy();
        expect(navigate).toHaveBeenCalled();
    });

    it("applies active classes when isActive is true", () => {
        const wrapper = mount(SidebarLink, {
            props: defaultProps,
            global: {
                stubs: {
                    RouterLink: {
                        template: '<slot :href="\'/test\'" :navigate="() => {}" :isActive="true" />',
                        props: ["to", "custom"],
                    },
                },
            },
        });
        expect(wrapper.find("a").classes()).toContain("bg-blue-100");
    });

    it("renders a link element", () => {
        const wrapper = mount(SidebarLink, {
            props: defaultProps,
            slots: { icon: "<span></span>", text: "<span>Link</span>" },
            global: { stubs: { RouterLink: RouterLinkStub } },
        });
        expect(wrapper.find("a").exists()).toBe(true);
    });

    it("link href comes from router slot when stubbed", () => {
        const to = { name: "settings" };
        const wrapper = mount(SidebarLink, {
            props: { ...defaultProps, to },
            slots: { icon: "<span></span>", text: "<span>Settings</span>" },
            global: {
                stubs: {
                    RouterLink: {
                        template:
                            '<slot :href="slotHref" :navigate="() => {}" :isActive="false"></slot>',
                        props: ["to"],
                        setup(props) {
                            const slotHref =
                                props.to && props.to.name
                                    ? `/route-${props.to.name}`
                                    : "#";
                            return { slotHref };
                        },
                    },
                },
            },
        });
        expect(wrapper.find("a").attributes("href")).toBe("/route-settings");
    });
});
