// SPDX-License-Identifier: 0BSD AND MIT
/**
 * Oracle: optimistic sidebar bump on compose enqueue must appear before WS ack.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import MessagesPage from "@/components/messages/MessagesPage.vue";

vi.mock("@/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

vi.mock("@/js/NotificationUtils", () => ({
    default: {
        clearMessageNotifications: vi.fn(),
        clearAllMessageNotifications: vi.fn(),
        showNewMessageNotification: vi.fn(),
        syncAndroidNotificationContext: vi.fn(),
    },
}));

const PEER = "bb".repeat(16);

describe("MessagesPage outbound compose oracle", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/config") {
                    return Promise.resolve({
                        data: { config: { lxmf_address_hash: "aa".repeat(16) } },
                    });
                }
                if (url === "/api/v1/lxmf/conversations") {
                    return Promise.resolve({ data: { conversations: [] } });
                }
                if (url === "/api/v1/announces") {
                    return Promise.resolve({ data: { announces: [] } });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
    });

    const mountPage = () =>
        mount(MessagesPage, {
            props: { destinationHash: "" },
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { replace: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LoadingSpinner: true,
                    MessagesSidebar: true,
                    ConversationViewer: true,
                    Modal: true,
                },
            },
        });

    it("onOutboundComposeEnqueued inserts conversation row with preview before server ack", async () => {
        const wrapper = mountPage();
        await flushPromises();
        expect(wrapper.vm.conversations).toHaveLength(0);

        wrapper.vm.onOutboundComposeEnqueued({
            peerHash: PEER,
            previewText: "hello optimistic",
            title: "",
            fields: {},
        });

        expect(wrapper.vm.conversations).toHaveLength(1);
        expect(wrapper.vm.conversations[0].destination_hash).toBe(PEER);
        expect(wrapper.vm.conversations[0].latest_message_preview).toContain("hello optimistic");
        expect(wrapper.vm.conversations[0].latest_message_created_at).toBeGreaterThan(0);
    });

    it("onOutboundComposeEnqueued updates existing row instead of duplicating", async () => {
        const wrapper = mountPage();
        await flushPromises();
        wrapper.vm.conversations = [
            {
                destination_hash: PEER,
                display_name: "Peer",
                latest_message_preview: "old",
                latest_message_created_at: 1,
                updated_at: new Date(1000).toISOString(),
            },
        ];

        wrapper.vm.onOutboundComposeEnqueued({
            peerHash: PEER,
            previewText: "new text",
            title: "t",
            fields: {},
        });

        expect(wrapper.vm.conversations).toHaveLength(1);
        expect(wrapper.vm.conversations[0].latest_message_preview).toContain("new text");
        expect(wrapper.vm.conversations[0].latest_message_title).toBe("t");
        expect(wrapper.vm.conversations[0].latest_message_created_at).toBeGreaterThan(1);
    });

    it("onOutboundComposeEnqueued ignores empty peerHash (must not create orphan row)", () => {
        const wrapper = mountPage();
        wrapper.vm.onOutboundComposeEnqueued({ peerHash: "", previewText: "x" });
        expect(wrapper.vm.conversations).toHaveLength(0);
    });
});
