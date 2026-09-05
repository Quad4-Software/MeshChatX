import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createI18n } from "vue-i18n";
import AppSidebarNav from "../../meshchatx/src/frontend/components/layout/AppSidebarNav.vue";
import AppSidebarClassicNav from "../../meshchatx/src/frontend/components/layout/AppSidebarClassicNav.vue";
import { NAV_EDIT_HOLD_MS } from "../../meshchatx/src/frontend/js/appSidebarNavLayout.js";
import { NAV_EDIT_CLICK_GUARD_MS } from "../../meshchatx/src/frontend/js/appSidebarNavEditHold.js";
import en from "../../meshchatx/src/frontend/locales/en.json";

const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: { en },
});

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

const groups = [
    {
        id: "communicate",
        items: [
            { id: "messages", route: { name: "messages" }, icon: "message-text", labelKey: "app.messages" },
            { id: "call", route: { name: "call" }, icon: "phone", labelKey: "app.audio_calls" },
        ],
    },
    {
        id: "app",
        items: [{ id: "settings", route: { name: "settings" }, icon: "cog", labelKey: "app.settings" }],
    },
];

function mountGrouped(props = {}) {
    return mount(AppSidebarNav, {
        attachTo: document.body,
        props: {
            primaryNavGroups: groups,
            moreNavItems: [{ id: "about", route: { name: "about" }, icon: "information", labelKey: "app.about" }],
            isCollapsed: false,
            isEditing: false,
            isShowingMoreNav: true,
            ...props,
        },
        global: {
            plugins: [i18n],
            stubs: {
                RouterLink: RouterLinkStub,
                MaterialDesignIcon: { template: '<span class="md-stub" />' },
            },
        },
    });
}

function dispatchHoldPointerDown(wrapperOrElement, overrides = {}) {
    const el = wrapperOrElement.element || wrapperOrElement;
    const evt = new PointerEvent("pointerdown", {
        bubbles: true,
        cancelable: true,
        pointerType: "touch",
        clientX: 10,
        clientY: 10,
        ...overrides,
    });
    el.dispatchEvent(evt);
    return evt;
}

function dispatchHoldPointerMove(wrapperOrElement, overrides = {}) {
    const el = wrapperOrElement.element || wrapperOrElement;
    const evt = new PointerEvent("pointermove", {
        bubbles: true,
        cancelable: true,
        pointerType: "touch",
        clientX: 10,
        clientY: 10,
        ...overrides,
    });
    el.dispatchEvent(evt);
    return evt;
}

describe("AppSidebarNav edit hold", () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it("emits edit-start after a hold on an expanded nav item", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        const item = wrapper.get('[data-nav-item-id="messages"]');
        dispatchHoldPointerDown(item);
        vi.advanceTimersByTime(NAV_EDIT_HOLD_MS + 10);
        expect(wrapper.emitted("edit-start")).toHaveLength(1);
        wrapper.unmount();
    });

    it("centers collapsed nav items and the More toggle", () => {
        const wrapper = mountGrouped({ isCollapsed: true });
        const more = wrapper.get('[data-testid="sidebar-more-toggle"]');
        expect(more.classes()).toContain("justify-center");
        expect(more.classes()).not.toContain("px-4");
        const item = wrapper.get('[data-nav-item-id="messages"]');
        expect(item.classes()).toContain("justify-center");
        const link = item.find(".sidebar-nav-link");
        expect(link.exists()).toBe(true);
        expect(link.classes()).toContain("justify-center");
        expect(link.classes()).not.toContain("mr-2");
        wrapper.unmount();
    });

    it("does not emit edit-start when the sidebar is collapsed", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped({ isCollapsed: true });
        const item = wrapper.get('[data-nav-item-id="messages"]');
        dispatchHoldPointerDown(item);
        vi.advanceTimersByTime(NAV_EDIT_HOLD_MS + 10);
        expect(wrapper.emitted("edit-start")).toBeUndefined();
        wrapper.unmount();
    });

    it("cancels hold when the pointer moves", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        const item = wrapper.get('[data-nav-item-id="messages"]');
        dispatchHoldPointerDown(item);
        dispatchHoldPointerMove(item, { clientX: 40, clientY: 40 });
        vi.advanceTimersByTime(NAV_EDIT_HOLD_MS + 10);
        expect(wrapper.emitted("edit-start")).toBeUndefined();
        wrapper.unmount();
    });

    it("emits edit-start after a hold on a section header", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        const header = wrapper.get('[data-group-id="communicate"]');
        expect(header.exists()).toBe(true);
        dispatchHoldPointerDown(header);
        vi.advanceTimersByTime(NAV_EDIT_HOLD_MS + 10);
        expect(wrapper.emitted("edit-start")).toHaveLength(1);
        wrapper.unmount();
    });

    it("shows move controls in edit mode and emits item-offset", async () => {
        const wrapper = mountGrouped({ isEditing: true });
        expect(wrapper.find('[data-testid="sidebar-nav"]').exists()).toBe(true);
        const up = wrapper
            .get('[data-nav-item-id="messages"]')
            .findAll("button")
            .find((btn) => btn.attributes("aria-label") === "Move up");
        expect(up).toBeTruthy();
        await up.trigger("click");
        expect(wrapper.emitted("nav-reorder")[0][0]).toEqual({
            kind: "item-offset",
            itemId: "messages",
            delta: -1,
        });
        wrapper.unmount();
    });

    it("classic nav centers collapsed items", () => {
        const wrapper = mount(AppSidebarClassicNav, {
            props: {
                navItems: groups[0].items,
                isCollapsed: true,
                isEditing: false,
            },
            global: {
                plugins: [i18n],
                stubs: {
                    RouterLink: RouterLinkStub,
                    MaterialDesignIcon: { template: '<span class="md-stub" />' },
                },
            },
        });
        const item = wrapper.get('[data-nav-item-id="messages"]');
        expect(item.classes()).toContain("justify-center");
        const link = item.find(".sidebar-nav-link");
        expect(link.exists()).toBe(true);
        expect(link.classes()).toContain("justify-center");
        wrapper.unmount();
    });

    it("classic nav also holds to edit when expanded", async () => {
        vi.useFakeTimers();
        const wrapper = mount(AppSidebarClassicNav, {
            attachTo: document.body,
            props: {
                navItems: groups[0].items,
                isCollapsed: false,
                isEditing: false,
            },
            global: {
                plugins: [i18n],
                stubs: {
                    RouterLink: RouterLinkStub,
                    MaterialDesignIcon: { template: '<span class="md-stub" />' },
                },
            },
        });
        const item = wrapper.get('[data-nav-item-id="messages"]');
        dispatchHoldPointerDown(item);
        vi.advanceTimersByTime(NAV_EDIT_HOLD_MS + 10);
        expect(wrapper.emitted("edit-start")).toHaveLength(1);
        wrapper.unmount();
    });

    it("does not capture the pointer on hold", async () => {
        const wrapper = mountGrouped();
        const setPointerCapture = vi.fn();
        const item = wrapper.get('[data-nav-item-id="messages"]');
        item.element.setPointerCapture = setPointerCapture;
        dispatchHoldPointerDown(item);
        expect(setPointerCapture).not.toHaveBeenCalled();
        wrapper.unmount();
    });

    it("does not swallow clicks after edit mode ends", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        const item = wrapper.get('[data-nav-item-id="messages"]');
        dispatchHoldPointerDown(item);
        vi.advanceTimersByTime(NAV_EDIT_HOLD_MS + 10);
        expect(wrapper.emitted("edit-start")).toHaveLength(1);
        await wrapper.setProps({ isEditing: true });
        await wrapper.setProps({ isEditing: false });
        const updatedItem = wrapper.get('[data-nav-item-id="messages"]');
        const clickEvt = new MouseEvent("click", { bubbles: true, cancelable: true });
        const preventDefault = vi.spyOn(clickEvt, "preventDefault");
        updatedItem.element.dispatchEvent(clickEvt);
        expect(preventDefault).not.toHaveBeenCalled();
        wrapper.unmount();
    });

    it("clears the hold click guard so later clicks can navigate", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        const item = wrapper.get('[data-nav-item-id="messages"]');
        dispatchHoldPointerDown(item);
        vi.advanceTimersByTime(NAV_EDIT_HOLD_MS + 10);
        expect(wrapper.emitted("edit-start")).toHaveLength(1);
        vi.advanceTimersByTime(NAV_EDIT_CLICK_GUARD_MS + 10);
        const clickEvt = new MouseEvent("click", { bubbles: true, cancelable: true });
        const preventDefault = vi.spyOn(clickEvt, "preventDefault");
        item.element.dispatchEvent(clickEvt);
        expect(preventDefault).not.toHaveBeenCalled();
        wrapper.unmount();
    });
});
