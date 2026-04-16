import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
    },
}));

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        connect: vi.fn(),
        destroy: vi.fn(),
    },
}));

vi.mock("@/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

function makeChatItems(count, myHash, peerHash) {
    return Array.from({ length: count }, (_, i) => ({
        type: "lxmf_message",
        is_outbound: i % 2 === 0,
        lxmf_message: {
            hash: `msg_${i}`.padEnd(32, "0"),
            source_hash: i % 2 === 0 ? myHash : peerHash,
            destination_hash: i % 2 === 0 ? peerHash : myHash,
            content: `Message content ${i}.`,
            created_at: new Date().toISOString(),
            state: "delivered",
            method: "direct",
            progress: 1.0,
            delivery_attempts: 1,
            id: i,
        },
    }));
}

function groupSignature(vm) {
    return vm.selectedPeerChatDisplayGroups.map((g) => `${g.type}:${g.key}`);
}

describe("ConversationViewer performance baselines", () => {
    const myLxmfAddressHash = "my_hash".padEnd(32, "0");
    const peerHash = "peer_hash".padEnd(32, "0");
    const selectedPeer = {
        destination_hash: peerHash,
        display_name: "Peer Name",
    };

    beforeEach(() => {
        window.api = {
            get: vi.fn(() => Promise.resolve({ data: {} })),
            post: vi.fn(() => Promise.resolve({ data: {} })),
        };
    });

    const mountViewer = () =>
        mount(ConversationViewer, {
            props: {
                myLxmfAddressHash,
                selectedPeer,
                conversations: [selectedPeer],
                config: { theme: "light", lxmf_address_hash: myLxmfAddressHash },
            },
            global: {
                components: {
                    MaterialDesignIcon: { template: "<span></span>" },
                    ConversationDropDownMenu: { template: "<div></div>" },
                    SendMessageButton: { template: "<div></div>" },
                    IconButton: { template: "<button></button>" },
                    AddImageButton: { template: "<div></div>" },
                    AddAudioButton: { template: "<div></div>" },
                    PaperMessageModal: { template: "<div></div>" },
                    AudioWaveformPlayer: { template: "<div></div>" },
                    LxmfUserIcon: { template: "<div></div>" },
                },
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
                mocks: {
                    $t: (key) => key,
                    $i18n: { locale: "en" },
                },
                stubs: {
                    MarkdownRenderer: true,
                },
            },
        });

    it("selectedPeerChatDisplayGroups signature is stable for a fixed thread (regression guard)", async () => {
        const wrapper = mountViewer();
        const items = makeChatItems(24, myLxmfAddressHash, peerHash);
        await wrapper.setData({ chatItems: items });
        await wrapper.vm.$nextTick();
        const sig = groupSignature(wrapper.vm);
        expect(sig.length).toBe(24);
        expect(sig[0]).toMatch(/^single:msg_/);
    });

    it("bulk chatItems update: baseline ceiling (detect regressions)", async () => {
        const wrapper = mountViewer();
        const n = 800;
        const items = makeChatItems(n, myLxmfAddressHash, peerHash);

        const t0 = performance.now();
        await wrapper.setData({ chatItems: items });
        await wrapper.vm.$nextTick();
        const ms = performance.now() - t0;

        expect(wrapper.vm.selectedPeerChatDisplayGroups.length).toBe(n);
        expect(ms).toBeLessThan(15000);
    }, 60_000);

    it("incremental append: baseline ceiling when thread already large", async () => {
        const wrapper = mountViewer();
        const n = 600;
        await wrapper.setData({ chatItems: makeChatItems(n, myLxmfAddressHash, peerHash) });
        await wrapper.vm.$nextTick();

        const newMsg = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "newmsg".padEnd(32, "0"),
                source_hash: myLxmfAddressHash,
                destination_hash: peerHash,
                content: "New",
                created_at: new Date().toISOString(),
                state: "delivered",
                method: "direct",
                progress: 1.0,
                delivery_attempts: 1,
                id: n,
            },
        };

        const t0 = performance.now();
        wrapper.vm.chatItems.push(newMsg);
        await wrapper.vm.$nextTick();
        const ms = performance.now() - t0;

        expect(wrapper.vm.selectedPeerChatDisplayGroups.length).toBe(n + 1);
        expect(ms).toBeLessThan(8000);
    }, 60_000);

    it("display groups computation alone stays bounded for large n", async () => {
        const wrapper = mountViewer();
        const n = 2000;
        await wrapper.setData({ chatItems: makeChatItems(n, myLxmfAddressHash, peerHash) });
        await wrapper.vm.$nextTick();

        const t0 = performance.now();
        for (let k = 0; k < 20; k++) {
            void wrapper.vm.selectedPeerChatDisplayGroups;
        }
        const ms = performance.now() - t0;

        expect(wrapper.vm.selectedPeerChatDisplayGroups.length).toBe(n);
        expect(ms).toBeLessThan(2000);
    }, 60_000);
});
