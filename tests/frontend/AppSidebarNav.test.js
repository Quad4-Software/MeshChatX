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

function holdEvent(overrides = {}) {
    return {
        pointerType: "touch",
        button: 0,
        clientX: 10,
        clientY: 10,
        currentTarget: { setPointerCapture() {} },
        preventDefault() {},
        stopPropagation() {},
        ...overrides,
    };
}

describe("AppSidebarNav edit hold", () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it("emits edit-start after a hold on an expanded nav item", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        wrapper.vm.onNavHoldPointerDown(holdEvent());
        await vi.advanceTimersByTimeAsync(NAV_EDIT_HOLD_MS);
        expect(wrapper.emitted("edit-start")).toHaveLength(1);
        wrapper.unmount();
    });

    it("does not emit edit-start when the sidebar is collapsed", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped({ isCollapsed: true });
        wrapper.vm.onNavHoldPointerDown(holdEvent());
        await vi.advanceTimersByTimeAsync(NAV_EDIT_HOLD_MS);
        expect(wrapper.emitted("edit-start")).toBeUndefined();
        wrapper.unmount();
    });

    it("cancels hold when the pointer moves", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        wrapper.vm.onNavHoldPointerDown(holdEvent());
        wrapper.vm.onNavHoldPointerMove(holdEvent({ clientX: 40, clientY: 40 }));
        await vi.advanceTimersByTimeAsync(NAV_EDIT_HOLD_MS);
        expect(wrapper.emitted("edit-start")).toBeUndefined();
        wrapper.unmount();
    });

    it("emits edit-start after a hold on a section header", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        expect(wrapper.get('[data-group-id="communicate"]').exists()).toBe(true);
        wrapper.vm.onNavHoldPointerDown(holdEvent());
        await vi.advanceTimersByTimeAsync(NAV_EDIT_HOLD_MS);
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

    it("classic nav also holds to edit when expanded", async () => {
        vi.useFakeTimers();
        const wrapper = mount(AppSidebarClassicNav, {
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
        await wrapper.get('[data-nav-item-id="messages"]');
        wrapper.vm.onNavHoldPointerDown(holdEvent());
        await vi.advanceTimersByTimeAsync(NAV_EDIT_HOLD_MS);
        expect(wrapper.emitted("edit-start")).toHaveLength(1);
        wrapper.unmount();
    });

    it("does not capture the pointer on hold", () => {
        const wrapper = mountGrouped();
        const setPointerCapture = vi.fn();
        wrapper.vm.onNavHoldPointerDown(holdEvent({ currentTarget: { setPointerCapture } }));
        expect(setPointerCapture).not.toHaveBeenCalled();
        wrapper.unmount();
    });

    it("does not swallow clicks after edit mode ends", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        wrapper.vm.onNavHoldPointerDown(holdEvent());
        await vi.advanceTimersByTimeAsync(NAV_EDIT_HOLD_MS);
        expect(wrapper.vm.navHoldArmed).toBe(true);
        await wrapper.setProps({ isEditing: true });
        await wrapper.setProps({ isEditing: false });
        expect(wrapper.vm.navHoldArmed).toBe(false);
        const event = { preventDefault: vi.fn(), stopPropagation: vi.fn() };
        wrapper.vm.onNavHoldClickCapture(event);
        expect(event.preventDefault).not.toHaveBeenCalled();
        expect(event.stopPropagation).not.toHaveBeenCalled();
        wrapper.unmount();
    });

    it("clears the hold click guard so later clicks can navigate", async () => {
        vi.useFakeTimers();
        const wrapper = mountGrouped();
        wrapper.vm.onNavHoldPointerDown(holdEvent());
        await vi.advanceTimersByTimeAsync(NAV_EDIT_HOLD_MS);
        expect(wrapper.vm.navHoldArmed).toBe(true);
        await vi.advanceTimersByTimeAsync(NAV_EDIT_CLICK_GUARD_MS);
        expect(wrapper.vm.navHoldArmed).toBe(false);
        wrapper.unmount();
    });
});
