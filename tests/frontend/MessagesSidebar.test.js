import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import MessagesSidebar from "@/components/messages/MessagesSidebar.vue";

describe("MessagesSidebar.vue", () => {
    beforeEach(() => {
        // Mock localStorage
        global.localStorage = {
            getItem: vi.fn(() => null),
            setItem: vi.fn(),
            removeItem: vi.fn(),
            clear: vi.fn(),
        };
    });

    const defaultProps = {
        peers: {},
        conversations: [],
        selectedDestinationHash: "",
        isLoading: false,
    };

    const mountMessagesSidebar = (props = {}) => {
        return mount(MessagesSidebar, {
            props: { ...defaultProps, ...props },
            global: {
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });
    };

    it("handles long conversation names and message previews with truncation", () => {
        const longName = "Very ".repeat(20) + "Long Name";
        const longPreview = "Message ".repeat(50);
        const conversations = [
            {
                destination_hash: "hash1",
                display_name: longName,
                latest_message_preview: longPreview,
                updated_at: new Date().toISOString(),
            },
        ];

        const wrapper = mountMessagesSidebar({ conversations });

        const nameElement = wrapper.find(".conversation-item .truncate");
        expect(nameElement.exists()).toBe(true);
        expect(nameElement.text()).toContain("Long Name");

        const previewElement = wrapper
            .findAll(".conversation-item .truncate")
            .find((el) => el.text().includes("Message"));
        expect(previewElement.exists()).toBe(true);
    });

    it("handles a large number of conversations with scroll overflow", async () => {
        const manyConversations = Array.from({ length: 100 }, (_, i) => ({
            destination_hash: `hash${i}`,
            display_name: `User ${i}`,
            latest_message_preview: `Last message ${i}`,
            updated_at: new Date().toISOString(),
        }));

        const wrapper = mountMessagesSidebar({ conversations: manyConversations });

        const scrollContainer = wrapper.find(".overflow-y-auto");
        expect(scrollContainer.exists()).toBe(true);
        expect(scrollContainer.classes()).toContain("overflow-y-auto");

        const conversationItems = wrapper.findAll(".conversation-item");
        expect(conversationItems.length).toBe(100);
    });

    it("handles long peer names in the announces tab", async () => {
        const longPeerName = "Peer ".repeat(20) + "Extreme Name";
        const peers = {
            peer1: {
                destination_hash: "peer1",
                display_name: longPeerName,
                updated_at: new Date().toISOString(),
                hops: 1,
            },
        };

        const wrapper = mountMessagesSidebar({ peers });

        // Switch to announces tab
        await wrapper.find("div.cursor-pointer:last-child").trigger("click");
        expect(wrapper.vm.tab).toBe("announces");

        const peerNameElement = wrapper.find(".truncate");
        expect(peerNameElement.exists()).toBe(true);
        expect(peerNameElement.text()).toContain("Extreme Name");
    });
});
