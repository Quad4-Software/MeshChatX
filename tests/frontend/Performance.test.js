import { cleanup, render } from "@testing-library/svelte";
import { describe, it, expect, vi } from "vitest";
import MessagesSidebar from "../../meshchatx/src/frontend/features/messages/components/MessagesSidebar.svelte";
import { visibleConversationItems } from "../../meshchatx/src/frontend/features/messages/lib/conversationViewerMessages.ts";

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
global.api = {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    isCancel: vi.fn().mockReturnValue(false),
};
window.api = global.api;

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
            destination_hash: i.toString(16).padStart(32, "0"),
            display_name: `Peer ${i}`,
            updated_at: new Date().toISOString(),
            latest_message_preview: `Latest message from peer ${i}`,
            is_unread: i % 10 === 0,
            failed_messages_count: i % 50 === 0 ? 1 : 0,
        }));

        const startMem = getMemoryUsage();
        const start = performance.now();

        const view = render(MessagesSidebar, {
            props: {
                conversations,
                peers: {},
                selectedDestinationHash: "",
                isLoading: false,
                isLoadingMore: false,
                hasMoreConversations: false,
            },
        });

        const end = performance.now();
        const endMem = getMemoryUsage();
        const renderTime = end - start;
        const memGrowth = endMem - startMem;

        console.log(
            `Rendered ${numConvs} conversations in ${renderTime.toFixed(2)}ms, Memory growth: ${memGrowth.toFixed(2)}MB`
        );

        expect(view.container.querySelectorAll("li")).toHaveLength(numConvs);
        expect(renderTime).toBeLessThan(12000);
        expect(memGrowth).toBeLessThan(256);
        cleanup();
    }, 60_000);

    it("measures performance of data updates in ConversationViewer", async () => {
        const numMsgs = 1000;
        const myLxmfAddressHash = "my_hash";
        const selectedPeer = {
            destination_hash: "peer_hash",
            display_name: "Peer Name",
        };

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
        const visible = visibleConversationItems(chatItems, selectedPeer.destination_hash, true);
        const end = performance.now();

        expect(visible).toHaveLength(numMsgs);
        console.log(`Filtered 1000 messages in ConversationViewer in ${(end - start).toFixed(2)}ms`);
        expect(end - start).toBeLessThan(12000);
    }, 30_000);
});
