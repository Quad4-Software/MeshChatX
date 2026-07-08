import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MessagesPage from "@/components/messages/MessagesPage.vue";
import NomadNetworkBrowser from "@/components/nomadnetwork/NomadNetworkBrowser.vue";
import { conversationListSignature, syncConversationListInPlace } from "@/js/lxmfConversationListSync";

const MAX_MESSAGES_MOUNT_MS = 2500;
const MAX_NOMAD_BROWSER_RESTORE_MS = 1500;

vi.mock("@/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

vi.mock("@/js/WebSocketConnection", () => ({
    default: { on: vi.fn(), off: vi.fn() },
}));

vi.mock("@/components/nomadnetwork/NomadNetworkPage.vue", () => ({
    default: {
        name: "NomadNetworkPage",
        template: '<div class="nnp-stub" :data-hash="destinationHash" :data-active="isActive ? \'1\' : \'0\'"></div>',
        props: {
            destinationHash: { type: String, default: "" },
            initialPath: { type: String, default: null },
            embedded: { type: Boolean, default: false },
            tabsEnabled: { type: Boolean, default: false },
            isActive: { type: Boolean, default: true },
        },
        emits: ["navigate", "open-node", "close-tab"],
    },
}));

const MaterialDesignIconStub = {
    name: "MaterialDesignIcon",
    template: '<div class="mdi-stub"></div>',
    props: ["iconName"],
};

describe("Mount load performance regressions", () => {
    describe("MessagesPage mount", () => {
        let axiosMock;

        beforeEach(() => {
            localStorage.clear();
            axiosMock = {
                get: vi.fn(),
                post: vi.fn(),
                isCancel: vi.fn(() => false),
            };
            window.api = axiosMock;
            axiosMock.get.mockImplementation((url) => {
                if (url === "/api/v1/config") {
                    return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
                }
                if (url === "/api/v1/lxmf/conversations") {
                    return Promise.resolve({ data: { conversations: [] } });
                }
                if (url === "/api/v1/lxmf/conversation-pins") {
                    return Promise.resolve({ data: { peer_hashes: [] } });
                }
                if (url === "/api/v1/lxmf/folders") {
                    return Promise.resolve({ data: { folders: [] } });
                }
                if (url === "/api/v1/announces") {
                    return Promise.resolve({ data: { announces: [] } });
                }
                return Promise.resolve({ data: {} });
            });
        });

        afterEach(() => {
            delete window.api;
        });

        const mountMessagesPage = () =>
            mount(MessagesPage, {
                props: { destinationHash: "" },
                global: {
                    mocks: {
                        $t: (key) => key,
                        $route: { query: {} },
                        $router: { replace: vi.fn() },
                    },
                    stubs: {
                        MaterialDesignIcon: MaterialDesignIconStub,
                        LoadingSpinner: true,
                        MessagesSidebar: {
                            template: '<div class="sidebar-stub"></div>',
                            props: ["conversations", "selectedDestinationHash"],
                        },
                        ConversationViewer: {
                            template: '<div class="viewer-stub"></div>',
                            props: ["selectedPeer", "myLxmfAddressHash"],
                        },
                        Modal: true,
                    },
                },
            });

        it("does not fetch lxmf delivery announces on initial mount", async () => {
            const wrapper = mountMessagesPage();
            await flushPromises();

            const announceCalls = axiosMock.get.mock.calls.filter(
                (call) => call[0] === "/api/v1/announces" && call[1]?.params?.aspect === "lxmf.delivery"
            );
            expect(announceCalls).toHaveLength(0);
            expect(wrapper.vm.announcesLoaded).toBe(false);
        });

        it("mounts within the messages page budget", async () => {
            const start = performance.now();
            mountMessagesPage();
            await flushPromises();
            const elapsed = performance.now() - start;
            expect(elapsed).toBeLessThan(MAX_MESSAGES_MOUNT_MS);
        });

        it("skips redundant conversation list replacement when polling returns the same signature", async () => {
            const conversations = Array.from({ length: 250 }, (_, index) => ({
                destination_hash: index.toString(16).padStart(32, "0"),
                display_name: `Peer ${index}`,
                updated_at: "2026-01-01T00:00:00Z",
                is_unread: index % 7 === 0,
                failed_messages_count: 0,
                latest_message_created_at: index,
                latest_message_preview: `Preview ${index}`,
            }));
            const signature = conversationListSignature(conversations);
            const existing = conversations.map((conversation) => ({ ...conversation }));
            const refsBefore = existing.map((conversation) => conversation);

            syncConversationListInPlace(
                existing,
                conversations.map((conversation) => ({ ...conversation }))
            );

            expect(conversationListSignature(existing)).toBe(signature);
            expect(existing.every((conversation, index) => conversation === refsBefore[index])).toBe(true);
        });
    });

    describe("NomadNetworkBrowser restore", () => {
        beforeEach(() => {
            localStorage.clear();
        });

        const mountBrowser = () =>
            mount(NomadNetworkBrowser, {
                global: {
                    mocks: {
                        $t: (key) => key,
                        $route: { name: "nomadnetwork", params: {}, query: {} },
                        $router: { replace: vi.fn(() => Promise.resolve()) },
                    },
                    stubs: {
                        MaterialDesignIcon: MaterialDesignIconStub,
                        NomadBrowserContextMenu: true,
                    },
                },
            });

        it("only mounts the active tab page when multiple tabs are restored", async () => {
            localStorage.setItem(
                "meshchatx.nomadnet.tabs",
                JSON.stringify({
                    tabs: [
                        { destinationHash: "a".repeat(32), path: null, title: "Alpha" },
                        { destinationHash: "b".repeat(32), path: null, title: "Bravo" },
                        { destinationHash: "c".repeat(32), path: null, title: "Charlie" },
                    ],
                    activeIndex: 1,
                })
            );

            const wrapper = mountBrowser();
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.tabs).toHaveLength(3);
            expect(wrapper.findAllComponents({ name: "NomadNetworkPage" })).toHaveLength(1);
            expect(wrapper.vm.isTabMounted(wrapper.vm.activeTabId)).toBe(true);
        });

        it("mounts inactive tabs lazily when they are selected", async () => {
            localStorage.setItem(
                "meshchatx.nomadnet.tabs",
                JSON.stringify({
                    tabs: [
                        { destinationHash: "a".repeat(32), path: null, title: "Alpha" },
                        { destinationHash: "b".repeat(32), path: null, title: "Bravo" },
                    ],
                    activeIndex: 0,
                })
            );

            const wrapper = mountBrowser();
            await wrapper.vm.$nextTick();
            const secondTabId = wrapper.vm.tabs[1].id;

            wrapper.vm.selectTab(secondTabId);
            await wrapper.vm.$nextTick();

            expect(wrapper.findAllComponents({ name: "NomadNetworkPage" })).toHaveLength(2);
            expect(wrapper.vm.isTabMounted(secondTabId)).toBe(true);
        });

        it("restores multiple tabs within the browser mount budget", async () => {
            localStorage.setItem(
                "meshchatx.nomadnet.tabs",
                JSON.stringify({
                    tabs: Array.from({ length: 8 }, (_, index) => ({
                        destinationHash: `${index}`.padStart(32, "a"),
                        path: null,
                        title: `Tab ${index}`,
                    })),
                    activeIndex: 3,
                })
            );

            const start = performance.now();
            const wrapper = mountBrowser();
            await wrapper.vm.$nextTick();
            const elapsed = performance.now() - start;

            expect(wrapper.vm.tabs).toHaveLength(8);
            expect(wrapper.findAllComponents({ name: "NomadNetworkPage" })).toHaveLength(1);
            expect(elapsed).toBeLessThan(MAX_NOMAD_BROWSER_RESTORE_MS);
        });
    });
});
