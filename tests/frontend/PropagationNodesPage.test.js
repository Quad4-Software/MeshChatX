// SPDX-License-Identifier: 0BSD

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/svelte";
import PropagationNodesPage from "@/features/propagation-nodes/PropagationNodesPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    bytesToMb,
    formatByteSize,
    formatDestinationHash,
    formatPathLabel,
    formatSeconds,
    formatStorageUsage,
    formatTimeAgo,
    mbToBytes,
} from "@/features/propagation-nodes/lib/propagationFormat.ts";
import { filterAndSortNodes } from "@/features/propagation-nodes/lib/propagationSort.ts";
import {
    fetchPropagationConfig,
    fetchPropagationNodes,
    restartLocalNode,
    stopLocalNode,
    triggerAnnounce,
    updatePropagationConfig,
} from "@/features/propagation-nodes/lib/propagationApi.ts";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

describe("propagationFormat", () => {
    beforeEach(() => {
        registerFallbackMessages({
            tools: {
                propagation_nodes: {
                    no_path: "No path yet",
                    hop_one: "1 hop",
                    hop_many: "{count} hops",
                    path_via: "{hops} via {iface}",
                    path_direct: "{hops}",
                },
            },
        });
    });

    it("converts bytes and MB accurately", () => {
        expect(bytesToMb(1000000)).toBe(1);
        expect(mbToBytes(2)).toBe(2000000);
    });

    it("formats byte sizes and storage usage", () => {
        expect(formatByteSize(1024)).toBe("1.0 KB");
        expect(
            formatStorageUsage({
                messagestore_bytes: 76500,
                messagestore_limit_bytes: 10240000,
            })
        ).toBe("76.5 KB / 10.24 MB");
    });

    it("formats seconds and time ago", () => {
        expect(formatSeconds(3600)).toBe("1h");
        expect(formatTimeAgo(null)).toBe("unknown");
    });

    it("formats destination hashes and path labels", () => {
        expect(formatDestinationHash("aabbccddeeff00112233445566778899")).toBe("<aabbccdd...66778899>");
        expect(formatPathLabel(null)).toBe("No path yet");
        expect(formatPathLabel({ hops: 2, next_hop_interface: "TCP" })).toBe("2 hops via TCP");
    });
});

describe("propagationSort", () => {
    it("filters and sorts nodes properly", () => {
        const nodes = [
            {
                destination_hash: "1111",
                operator_display_name: "Beta Node",
                updated_at: "2026-01-01T00:00:00Z",
                hops: 2,
            },
            {
                destination_hash: "2222",
                operator_display_name: "Alpha Node",
                updated_at: "2026-01-02T00:00:00Z",
                hops: 1,
            },
        ];

        const sortedByName = filterAndSortNodes(nodes, "", "name", "");
        expect(sortedByName[0].operator_display_name).toBe("Alpha Node");

        const sortedByRecent = filterAndSortNodes(nodes, "", "recent", "");
        expect(sortedByRecent[0].destination_hash).toBe("2222");

        const filtered = filterAndSortNodes(nodes, "Beta", "name", "");
        expect(filtered).toHaveLength(1);
        expect(filtered[0].operator_display_name).toBe("Beta Node");
    });
});

describe("propagationApi", () => {
    beforeEach(() => {
        window.api = {
            get: vi.fn(async (url) => {
                if (url.includes("/api/v1/config")) {
                    return { data: { config: { lxmf_preferred_propagation_node: "1234" } } };
                }
                if (url.includes("/api/v1/lxmf/propagation-nodes")) {
                    return {
                        data: {
                            lxmf_propagation_nodes: [
                                {
                                    destination_hash: "1234",
                                    is_local_node: true,
                                    operator_display_name: "My Local Node",
                                },
                            ],
                        },
                    };
                }
                return { data: {} };
            }),
            post: vi.fn(async () => ({ data: {} })),
            patch: vi.fn(async (url, data) => ({ data: { config: data } })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    it("fetches and updates config", async () => {
        const config = await fetchPropagationConfig();
        expect(config.lxmf_preferred_propagation_node).toBe("1234");

        await updatePropagationConfig({ lxmf_preferred_propagation_node: "5678" });
        expect(window.api.patch).toHaveBeenCalledWith("/api/v1/config", {
            lxmf_preferred_propagation_node: "5678",
        });
    });

    it("fetches nodes and triggers announce / node control", async () => {
        const nodes = await fetchPropagationNodes();
        expect(nodes).toHaveLength(1);

        await triggerAnnounce();
        expect(window.api.get).toHaveBeenCalledWith("/api/v1/announce");

        await stopLocalNode();
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/lxmf/propagation-node/stop");

        await restartLocalNode();
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/lxmf/propagation-node/restart");
    });
});

describe("PropagationNodesPage.svelte component", () => {
    beforeEach(() => {
        cleanup();
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            propagation_nodes: {
                title: "Propagation Nodes",
                description: "Manage propagation nodes",
                hosted_node: "Hosted Node",
                preferred_node: "Preferred Node",
                search_placeholder: "Search nodes...",
                no_nodes_found: "No propagation nodes found",
            },
        });
        window.api = {
            get: vi.fn(async (url) => {
                if (url.includes("/api/v1/config")) {
                    return { data: { config: { lxmf_preferred_propagation_node: "1234" } } };
                }
                if (url.includes("/api/v1/lxmf/propagation-nodes")) {
                    return {
                        data: {
                            lxmf_propagation_nodes: [
                                {
                                    destination_hash: "1234",
                                    is_local_node: false,
                                    operator_display_name: "Community Node",
                                },
                            ],
                        },
                    };
                }
                return { data: {} };
            }),
            post: vi.fn(async () => ({ data: {} })),
            patch: vi.fn(async () => ({ data: {} })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    afterEach(() => {
        cleanup();
    });

    it("mounts and loads propagation nodes", async () => {
        const { getByTestId } = render(PropagationNodesPage);
        await waitFor(() => {
            expect(getByTestId("propagation-nodes-page")).toBeTruthy();
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/config");
        });
    });
});
