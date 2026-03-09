import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import MessagesSidebar from "../../meshchatx/src/frontend/components/messages/MessagesSidebar.vue";
import ConversationViewer from "../../meshchatx/src/frontend/components/messages/ConversationViewer.vue";

// Mock dependencies
vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        config: { theme: "light", banished_effect_enabled: false },
        blockedDestinations: [],
    },
}));

vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: {
        formatTimeAgo: () => "1 hour ago",
        formatBytes: () => "1 KB",
        formatDestinationHash: (h) => h,
        convertUnixMillisToLocalDateTimeString: (ms) => "2026-01-01 12:00 PM",
        convertDateTimeToLocalDateTimeString: (dt) => "2026-01-01 12:00 PM",
        escapeHtml: (t) =>
            t.replace(
                /[&<>"']/g,
                (m) =>
                    ({
                        "&": "&amp;",
                        "<": "&lt;",
                        ">": "&gt;",
                        '"': "&quot;",
                        "'": "&#039;",
                    })[m]
            ),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

// Mock axios
global.axios = {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
};
window.axios = global.axios;

// Mock localStorage
const localStorageMock = {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    clear: vi.fn(),
};
global.localStorage = localStorageMock;

// Mock MaterialDesignIcon
const MaterialDesignIcon = {
    template: '<div class="mdi"></div>',
    props: ["iconName"],
};

describe("UI Performance and Memory Tests", () => {
    const getMemoryUsage = () => {
        if (global.process && process.memoryUsage) {
            return process.memoryUsage().heapUsed / (1024 * 1024);
        }
        return 0;
    };

    it("renders MessagesSidebar with 2000 conversations quickly and tracks memory", async () => {
        const numConvs = 2000;
        const conversations = Array.from({ length: numConvs }, (_, i) => ({
            destination_hash: `hash_${i}`.padEnd(32, "0"),
            display_name: `Peer ${i}`,
            updated_at: new Date().toISOString(),
            latest_message_preview: `Latest message from peer ${i}`,
            is_unread: i % 10 === 0,
            failed_messages_count: i % 50 === 0 ? 1 : 0,
        }));

        const startMem = getMemoryUsage();
        const start = performance.now();

        const wrapper = mount(MessagesSidebar, {
            props: {
                conversations,
                peers: {},
                selectedDestinationHash: "",
                isLoading: false,
                isLoadingMore: false,
                hasMoreConversations: false,
            },
            global: {
                components: {
                    MaterialDesignIcon,
                    LxmfUserIcon: { template: '<div class="lxmf-icon"></div>' },
                },
                mocks: { $t: (key) => key },
            },
        });

        const end = performance.now();
        const endMem = getMemoryUsage();
        const renderTime = end - start;
        const memGrowth = endMem - startMem;

        console.log(
            `Rendered ${numConvs} conversations in ${renderTime.toFixed(2)}ms, Memory growth: ${memGrowth.toFixed(2)}MB`
        );

        expect(wrapper.findAll(".conversation-item").length).toBe(numConvs);
        expect(renderTime).toBeLessThan(5000);
        expect(memGrowth).toBeLessThan(200); // Adjusted for JSDOM/Node.js overhead with 2000 items
    });

    it("measures performance of data updates in ConversationViewer", async () => {
        const numMsgs = 1000;
        const myLxmfAddressHash = "my_hash";
        const selectedPeer = {
            destination_hash: "peer_hash",
            display_name: "Peer Name",
        };

        const wrapper = mount(ConversationViewer, {
            props: {
                myLxmfAddressHash,
                selectedPeer,
                conversations: [selectedPeer],
                config: { theme: "light", lxmf_address_hash: myLxmfAddressHash },
            },
            global: {
                components: {
                    MaterialDesignIcon,
                    ConversationDropDownMenu: { template: "<div></div>" },
                    SendMessageButton: { template: "<div></div>" },
                    IconButton: { template: "<button></button>" },
                    AddImageButton: { template: "<div></div>" },
                    AddAudioButton: { template: "<div></div>" },
                    PaperMessageModal: { template: "<div></div>" },
                },
                mocks: {
                    $t: (key) => key,
                    $i18n: { locale: "en" },
                },
            },
        });

        const chatItems = Array.from({ length: numMsgs }, (_, i) => ({
            type: "lxmf_message",
            is_outbound: i % 2 === 0,
            lxmf_message: {
                hash: `msg_${i}`.padEnd(32, "0"),
                source_hash: i % 2 === 0 ? myLxmfAddressHash : "peer_hash",
                destination_hash: i % 2 === 0 ? "peer_hash" : myLxmfAddressHash,
                content: `Message content ${i}.`.repeat(5),
                created_at: new Date().toISOString(),
                state: "delivered",
                method: "direct",
                progress: 1.0,
                delivery_attempts: 1,
                id: i,
            },
        }));

        const start = performance.now();
        await wrapper.setData({ chatItems });
        const end = performance.now();

        console.log(`Updated 1000 messages in ConversationViewer in ${(end - start).toFixed(2)}ms`);
        expect(end - start).toBeLessThan(5000);
    });
});
