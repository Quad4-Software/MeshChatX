import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import ConversationPeerHeader from "../../meshchatx/src/frontend/components/messages/ConversationPeerHeader.vue";

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
                IconButton: true,
                DropDownMenu: {
                    template: '<div class="dd" v-bind="$attrs"><slot name="button" /><slot name="items" /></div>',
                },
                DropDownMenuItem: true,
                LxmfUserIcon: true,
                ConversationDropDownMenu: {
                    name: "ConversationDropDownMenu",
                    props: ["peer", "compact", "hasFailedMessages", "pathfinderInProgress"],
                    template: '<div data-testid="conversation-menu"></div>',
                },
            },
        },
    });
}

describe("ConversationPeerHeader.vue path row", () => {
    it("shows hop count for a fresh path", () => {
        const wrapper = mountHeader({
            selectedPeerPath: { hops: 2, next_hop: "b".repeat(32), next_hop_interface: "UDP" },
            peerPathSnapshot: { path: { hops: 2 }, path_stale: false, path_unresponsive: false },
        });
        expect(wrapper.text()).toContain("messages.hops_away");
    });

    it("shows no path when snapshot has no route", () => {
        const wrapper = mountHeader({
            selectedPeerPath: null,
            peerPathSnapshot: { path: null, path_stale: true, path_unresponsive: false },
        });
        expect(wrapper.text()).toContain("messages.path_no_route");
    });

    it("shows finding path while warming", () => {
        const wrapper = mountHeader({
            peerPathWarming: true,
        });
        expect(wrapper.text()).toContain("messages.outbound_pathfinding_short");
    });

    it("marks stale paths in the label", () => {
        const wrapper = mountHeader({
            selectedPeerPath: { hops: 1, next_hop: "b".repeat(32), next_hop_interface: "UDP" },
            peerPathSnapshot: { path: { hops: 1 }, path_stale: true, path_unresponsive: false },
        });
        expect(wrapper.text()).toContain("messages.path_stale_label");
    });

    it("hides path-ops icon when compactPeerActions is true", () => {
        const wrapper = mountHeader({ compactPeerActions: true });
        expect(wrapper.find('[data-testid="conversation-path-ops"]').exists()).toBe(false);
    });

    it("shows path-ops icon when compactPeerActions is false", () => {
        const wrapper = mountHeader({ compactPeerActions: false });
        expect(wrapper.find('[data-testid="conversation-path-ops"]').exists()).toBe(true);
    });
});
