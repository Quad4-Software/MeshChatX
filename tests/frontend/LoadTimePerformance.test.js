import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PropagationNodesPage from "../../meshchatx/src/frontend/components/propagation-nodes/PropagationNodesPage.vue";
import MessagesSidebar from "../../meshchatx/src/frontend/components/messages/MessagesSidebar.vue";
import NomadNetworkSidebar from "../../meshchatx/src/frontend/components/nomadnetwork/NomadNetworkSidebar.vue";

const MAX_PROP_NODES_MS = 3000;
const MAX_MESSAGES_ANNOUNCES_MS = 12000;
const MAX_NOMADNET_NODES_MS = 3000;

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: { on: vi.fn(), off: vi.fn(), send: vi.fn() },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        config: { theme: "light", banished_effect_enabled: false },
        blockedDestinations: [],
    },
}));

vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: {
        formatTimeAgo: (d) => "1h ago",
        formatDestinationHash: (h) => (h && h.length >= 8 ? h.slice(0, 8) + "…" : h),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

const MaterialDesignIcon = { template: '<div class="mdi"></div>', props: ["iconName"] };
const LxmfUserIcon = { template: '<div class="lxmf-icon"></div>' };

function makePropagationNode(i) {
    return {
        destination_hash: `dest_${i}`.padEnd(32, "0").slice(0, 32),
        operator_display_name: `Prop Node Operator ${i}`,
        updated_at: new Date(Date.now() - i * 60000).toISOString(),
        is_propagation_enabled: true,
    };
}

function makePeer(i) {
    const hash = `p${String(i).padStart(31, "0")}`;
    return {
        destination_hash: hash,
        display_name: `Peer ${i}`,
        updated_at: new Date(Date.now() - i * 60000).toISOString(),
        hops: i % 3,
        snr: 10 + (i % 5),
    };
}

function makeNomadNode(i) {
    const hash = `n${String(i).padStart(31, "0")}`;
    return {
        destination_hash: hash,
        identity_hash: `i${String(i).padStart(31, "0")}`,
        display_name: `Nomad Node ${i}`,
        updated_at: new Date(Date.now() - i * 60000).toISOString(),
    };
}

describe("Load time with prefilled data", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe("Propagation nodes section", () => {
        it("loads and renders 500 propagation nodes within threshold", async () => {
            const count = 500;
            const nodes = Array.from({ length: count }, (_, i) => makePropagationNode(i));

            const axiosGet = vi.fn((url) => {
                if (url === "/api/v1/config") {
                    return Promise.resolve({
                        data: {
                            config: { lxmf_preferred_propagation_node_destination_hash: null },
                        },
                    });
                }
                if (url.startsWith("/api/v1/lxmf/propagation-nodes")) {
                    return Promise.resolve({ data: { lxmf_propagation_nodes: nodes } });
                }
                return Promise.resolve({ data: {} });
            });
            window.api = {
                get: axiosGet,
                patch: vi.fn(() => Promise.resolve({ data: {} })),
                isCancel: vi.fn().mockReturnValue(false),
            };

            const start = performance.now();
            const wrapper = mount(PropagationNodesPage, {
                global: {
                    mocks: { $t: (key) => key },
                },
            });
            await flushPromises();
            await wrapper.vm.$nextTick();
            const end = performance.now();
            const loadMs = end - start;

            expect(wrapper.vm.propagationNodes.length).toBe(count);
            expect(wrapper.vm.paginatedNodes.length).toBe(20);
            expect(loadMs).toBeLessThan(MAX_PROP_NODES_MS);
            if (process.env.CI !== "true") {
                console.log(
                    `Propagation nodes: ${count} nodes loaded in ${loadMs.toFixed(0)}ms (max ${MAX_PROP_NODES_MS}ms)`
                );
            }
        });
    });

    describe("Messages section", () => {
        it("renders sidebar with 2000 conversations within threshold", async () => {
            const count = 2000;
            const conversations = Array.from({ length: count }, (_, i) => ({
                destination_hash: `hash_${i}`.padEnd(32, "0").slice(0, 32),
                display_name: `Peer ${i}`,
                updated_at: new Date().toISOString(),
                latest_message_preview: `Preview ${i}`,
                is_unread: i % 10 === 0,
                failed_messages_count: 0,
            }));

            const start = performance.now();
            const wrapper = mount(MessagesSidebar, {
                props: {
                    conversations,
                    peers: {},
                    selectedDestinationHash: "",
                    isLoading: false,
                    isLoadingMore: false,
                    hasMoreConversations: false,
                    hasMoreAnnounces: false,
                    isLoadingMoreAnnounces: false,
                    totalPeersCount: 0,
                },
                global: {
                    components: { MaterialDesignIcon, LxmfUserIcon },
                    mocks: { $t: (key) => key },
                },
            });
            await wrapper.vm.$nextTick();
            const end = performance.now();

            expect(wrapper.vm.displayedConversations.length).toBe(count);
            expect(end - start).toBeLessThan(MAX_MESSAGES_ANNOUNCES_MS);
            if (process.env.CI !== "true") {
                console.log(
                    `Messages: ${count} conversations in ${(end - start).toFixed(0)}ms (max ${MAX_MESSAGES_ANNOUNCES_MS}ms)`
                );
            }
        });
    });

    describe("Announces section (messages sidebar)", () => {
        it("renders announces tab with 1500 peers within threshold", async () => {
            const count = 1500;
            const peers = Object.fromEntries(
                Array.from({ length: count }, (_, i) => {
                    const p = makePeer(i);
                    return [p.destination_hash, p];
                })
            );

            const start = performance.now();
            const wrapper = mount(MessagesSidebar, {
                props: {
                    conversations: [],
                    peers,
                    selectedDestinationHash: "",
                    isLoading: false,
                    isLoadingMore: false,
                    hasMoreConversations: false,
                    hasMoreAnnounces: false,
                    isLoadingMoreAnnounces: false,
                    totalPeersCount: count,
                },
                global: {
                    components: { MaterialDesignIcon, LxmfUserIcon },
                    mocks: { $t: (key) => key },
                },
            });
            await wrapper.vm.$nextTick();
            wrapper.vm.tab = "announces";
            await wrapper.vm.$nextTick();
            const end = performance.now();

            expect(wrapper.vm.peersOrderedByLatestAnnounce.length).toBe(count);
            expect(wrapper.vm.searchedPeers.length).toBe(count);
            expect(end - start).toBeLessThan(MAX_MESSAGES_ANNOUNCES_MS);
            if (process.env.CI !== "true") {
                console.log(
                    `Announces (messages): ${count} peers in ${(end - start).toFixed(0)}ms (max ${MAX_MESSAGES_ANNOUNCES_MS}ms)`
                );
            }
        }, 20000);
    });

    describe("NomadNet nodes section", () => {
        it("renders sidebar announces tab with 800 nodes within threshold", async () => {
            const count = 800;
            const nodes = Object.fromEntries(
                Array.from({ length: count }, (_, i) => {
                    const n = makeNomadNode(i);
                    return [n.destination_hash, n];
                })
            );

            const start = performance.now();
            const wrapper = mount(NomadNetworkSidebar, {
                props: {
                    nodes,
                    favourites: [],
                    selectedDestinationHash: "",
                    nodesSearchTerm: "",
                    totalNodesCount: count,
                    isLoadingMoreNodes: false,
                    hasMoreNodes: false,
                },
                global: {
                    components: {
                        MaterialDesignIcon,
                        IconButton: { template: "<button></button>" },
                        DropDownMenu: { template: '<div><slot name="button"/><slot name="items"/></div>' },
                        DropDownMenuItem: { template: "<div></div>" },
                    },
                    mocks: { $t: (key) => key },
                },
            });
            wrapper.vm.tab = "announces";
            await wrapper.vm.$nextTick();
            const end = performance.now();

            expect(wrapper.vm.searchedNodes.length).toBe(count);
            expect(end - start).toBeLessThan(MAX_NOMADNET_NODES_MS);
            if (process.env.CI !== "true") {
                console.log(
                    `NomadNet nodes: ${count} nodes in ${(end - start).toFixed(0)}ms (max ${MAX_NOMADNET_NODES_MS}ms)`
                );
            }
        });
    });
});
