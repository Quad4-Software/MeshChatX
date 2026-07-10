import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationPeerHeader from "../../meshchatx/src/frontend/components/messages/ConversationPeerHeader.vue";
import ConversationDropDownMenu from "../../meshchatx/src/frontend/components/messages/ConversationDropDownMenu.vue";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState.js";

const peer = {
    destination_hash: "a".repeat(32),
    display_name: "Test Peer",
};

function mountHeader(props = {}) {
    return mount(ConversationPeerHeader, {
        props: {
            selectedPeer: peer,
            ...props,
        },
        global: {
            mocks: { $t: (key) => key },
            stubs: {
                MaterialDesignIcon: true,
                IconButton: {
                    template: '<button type="button" v-bind="$attrs"><slot /></button>',
                },
                DropDownMenu: {
                    template:
                        '<div class="dd"><slot name="button" /><div class="dd-items"><slot name="items" /></div></div>',
                },
                DropDownMenuItem: {
                    template: '<div class="dd-item" v-bind="$attrs" @click="$emit(\'click\')"><slot /></div>',
                },
                LxmfUserIcon: true,
                ConversationDropDownMenu: {
                    name: "ConversationDropDownMenu",
                    props: ["peer", "compact", "hasFailedMessages", "pathfinderInProgress"],
                    template:
                        "<div data-testid=\"conversation-menu\" :data-compact=\"compact ? '1' : '0'\" :data-pathfinder=\"pathfinderInProgress ? '1' : '0'\"></div>",
                    emits: [
                        "path-finder-quick",
                        "path-finder-force",
                        "path-finder-drop",
                        "popout",
                        "conversation-deleted",
                        "set-custom-display-name",
                        "retry-failed",
                        "open-telemetry-history",
                        "start-call",
                        "share-contact",
                    ],
                },
            },
        },
    });
}

function mountMenu(props = {}) {
    return mount(ConversationDropDownMenu, {
        props: {
            peer,
            ...props,
        },
        global: {
            mocks: { $t: (key) => key },
            stubs: {
                MaterialDesignIcon: {
                    props: ["iconName"],
                    template: '<span class="mdi" :data-icon="iconName"></span>',
                },
                IconButton: {
                    template: '<button type="button" v-bind="$attrs"><slot /></button>',
                },
                DropDownMenu: {
                    template:
                        '<div class="dd"><slot name="button" /><div class="dd-items"><slot name="items" /></div></div>',
                },
                DropDownMenuItem: {
                    emits: ["click"],
                    template: '<div class="dd-item" v-bind="$attrs" @click="$emit(\'click\')"><slot /></div>',
                },
            },
        },
    });
}

describe("conversation mobile chrome", () => {
    beforeEach(() => {
        GlobalState.blockedDestinations = [];
        GlobalState.config = { telemetry_enabled: false };
        window.api = {
            get: vi.fn().mockResolvedValue({ data: { is_contact: false } }),
        };
    });

    afterEach(() => {
        delete window.api;
    });

    it("hides standalone path-ops icon on mobile compact header", () => {
        const wrapper = mountHeader({ compactPeerActions: true });
        expect(wrapper.find('[data-testid="conversation-path-ops"]').exists()).toBe(false);
        expect(wrapper.find('[data-testid="conversation-menu"]').attributes("data-compact")).toBe("1");
    });

    it("shows standalone path-ops icon on desktop header", () => {
        const wrapper = mountHeader({ compactPeerActions: false });
        expect(wrapper.find('[data-testid="conversation-path-ops"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="conversation-menu"]').attributes("data-compact")).toBe("0");
    });

    it("puts path finder actions in compact 3-dots menu and hides popout", async () => {
        const wrapper = mountMenu({ compact: true });
        await wrapper.vm.$nextTick();

        expect(wrapper.find('[data-testid="path-finder-quick"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="path-finder-force"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="path-finder-drop"]').exists()).toBe(true);
        expect(wrapper.text()).toContain("nomadnet.path_finder_quick_request");
        expect(wrapper.text()).not.toContain("messages.pop_out_chat");
        expect(wrapper.find('[data-testid="conversation-popout"]').exists()).toBe(false);
    });

    it("emits path finder events from compact menu", async () => {
        const wrapper = mountMenu({ compact: true });
        await wrapper.vm.$nextTick();

        await wrapper.find('[data-testid="path-finder-quick"]').trigger("click");
        await wrapper.find('[data-testid="path-finder-force"]').trigger("click");
        await wrapper.find('[data-testid="path-finder-drop"]').trigger("click");

        expect(wrapper.emitted("path-finder-quick")).toHaveLength(1);
        expect(wrapper.emitted("path-finder-force")).toHaveLength(1);
        expect(wrapper.emitted("path-finder-drop")).toHaveLength(1);
    });

    it("keeps popout on desktop non-compact menu", async () => {
        const wrapper = mountMenu({ compact: false });
        await wrapper.vm.$nextTick();

        expect(wrapper.find('[data-testid="conversation-popout"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="path-finder-quick"]').exists()).toBe(false);
    });
});
