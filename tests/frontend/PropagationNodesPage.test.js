import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PropagationNodesPage from "../../meshchatx/src/frontend/components/propagation-nodes/PropagationNodesPage.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe("PropagationNodesPage", () => {
    const axiosMock = {
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
    };

    beforeEach(() => {
        vi.useFakeTimers();
        vi.clearAllMocks();
        window.api = axiosMock;
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("finds local propagation node from list", () => {
        const ctx = {
            propagationNodes: [
                { destination_hash: "remote-a", is_local_node: false },
                { destination_hash: "local-node", is_local_node: true },
            ],
        };
        const local = PropagationNodesPage.computed.localPropagationNode.call(ctx);
        expect(local.destination_hash).toBe("local-node");
    });

    it("uses local propagation node as preferred", async () => {
        const ctx = {
            localPropagationNode: { destination_hash: "local-node" },
            usePropagationNode: vi.fn(),
            requestPathForNode: vi.fn(),
        };

        await PropagationNodesPage.methods.useLocalPropagationNode.call(ctx);
        expect(ctx.usePropagationNode).toHaveBeenCalledWith("local-node");
        expect(ctx.requestPathForNode).toHaveBeenCalledWith("local-node");
    });

    it("prefers runtime local node state for running indicator", () => {
        const runningByStats = PropagationNodesPage.computed.localNodeIsRunning.call({
            localPropagationNode: {
                is_propagation_enabled: true,
                local_node_stats: { is_running: false },
            },
        });
        expect(runningByStats).toBe(false);
    });

    it("formats storage usage with limit when available", () => {
        const ctx = {
            formatByteSize: PropagationNodesPage.methods.formatByteSize,
        };
        const text = PropagationNodesPage.methods.formatStorageUsage.call(ctx, {
            messagestore_bytes: 76500,
            messagestore_limit_bytes: 10240000,
        });
        expect(text).toBe("76.5 KB / 10.24 MB");
    });

    it("debounces propagation transfer limit save", async () => {
        const ctx = {
            propagationLimitInputMb: 1.234,
            saveTimeouts: {
                propagationLimit: null,
            },
            mbToBytes: PropagationNodesPage.methods.mbToBytes,
            updateConfig: vi.fn().mockResolvedValue(undefined),
        };

        await PropagationNodesPage.methods.onPropagationTransferLimitChange.call(ctx);
        expect(ctx.updateConfig).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(500);
        expect(ctx.updateConfig).toHaveBeenCalledWith({
            lxmf_propagation_transfer_limit_in_bytes: 1234000,
        });
    });

    it("debounces propagation stamp cost save with bounds", async () => {
        const ctx = {
            config: {
                lxmf_propagation_node_stamp_cost: 3,
            },
            saveTimeouts: {
                propagationStampCost: null,
            },
            updateConfig: vi.fn().mockResolvedValue(undefined),
        };
        await PropagationNodesPage.methods.onPropagationStampCostChange.call(ctx);
        await vi.advanceTimersByTimeAsync(500);
        expect(ctx.updateConfig).toHaveBeenCalledWith({
            lxmf_propagation_node_stamp_cost: 13,
        });
    });

    it("stops and restarts local node via API", async () => {
        axiosMock.post.mockResolvedValue({ data: {} });
        const ctx = {
            getConfig: vi.fn().mockResolvedValue(undefined),
            loadPropagationNodes: vi.fn().mockResolvedValue(undefined),
            refreshPriorityNodePaths: vi.fn().mockResolvedValue(undefined),
            $t: (k) => k,
        };

        await PropagationNodesPage.methods.stopLocalPropagationNode.call(ctx);
        await PropagationNodesPage.methods.restartLocalPropagationNode.call(ctx);

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/lxmf/propagation-node/stop");
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/lxmf/propagation-node/restart");
        expect(ToastUtils.success).toHaveBeenCalledTimes(2);
    });

    it("triggers announce via icon action", async () => {
        axiosMock.get.mockResolvedValue({ data: {} });
        const ctx = {
            loadPropagationNodes: vi.fn().mockResolvedValue(undefined),
            refreshPriorityNodePaths: vi.fn().mockResolvedValue(undefined),
            $t: (k) => k,
        };
        await PropagationNodesPage.methods.announceNow.call(ctx);
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announce");
        expect(ToastUtils.success).toHaveBeenCalledWith("Announce triggered");
    });

    it("resets local node display name to Anonymous Peer", async () => {
        const ctx = {
            localNodeDisplayNameDraft: "Custom Name",
            saveLocalNodeDisplayName: vi.fn().mockResolvedValue(undefined),
        };
        await PropagationNodesPage.methods.resetLocalNodeDisplayName.call(ctx);
        expect(ctx.localNodeDisplayNameDraft).toBe("Anonymous Peer");
        expect(ctx.saveLocalNodeDisplayName).toHaveBeenCalledTimes(1);
    });

    it("uses collapsed manager on small screens", () => {
        const originalMatchMedia = window.matchMedia;
        window.matchMedia = vi.fn().mockReturnValue({ matches: true });
        const ctx = {
            isLocalManagerCollapsed: false,
            getConfig: vi.fn(),
            loadPropagationNodes: vi.fn(),
            refreshPriorityNodePaths: vi.fn(),
        };
        PropagationNodesPage.mounted.call(ctx);
        expect(ctx.isLocalManagerCollapsed).toBe(true);
        window.matchMedia = originalMatchMedia;
    });

    it("saves local display name and announces immediately", async () => {
        axiosMock.patch.mockResolvedValue({
            data: {
                config: {
                    display_name: "Friendly Node",
                    lxmf_delivery_transfer_limit_in_bytes: 10000000,
                    lxmf_propagation_transfer_limit_in_bytes: 256000,
                    lxmf_propagation_sync_limit_in_bytes: 10240000,
                },
            },
        });
        axiosMock.get.mockResolvedValue({ data: {} });

        const ctx = {
            localNodeDisplayNameDraft: " Friendly Node ",
            config: {
                lxmf_delivery_transfer_limit_in_bytes: 10000000,
                lxmf_propagation_transfer_limit_in_bytes: 256000,
                lxmf_propagation_sync_limit_in_bytes: 10240000,
            },
            syncManagerInputsFromConfig: vi.fn(),
            loadPropagationNodes: vi.fn().mockResolvedValue(undefined),
            refreshPriorityNodePaths: vi.fn().mockResolvedValue(undefined),
            announceNow: PropagationNodesPage.methods.announceNow,
            updateConfig: PropagationNodesPage.methods.updateConfig,
            $t: (k) => k,
        };

        await PropagationNodesPage.methods.saveLocalNodeDisplayName.call(ctx);

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/config", {
            display_name: "Friendly Node",
        });
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announce");
        expect(ToastUtils.success).toHaveBeenCalledWith("Name saved and announced");
    });

    it("fetches path for a destination hash", async () => {
        axiosMock.get.mockResolvedValueOnce({
            data: {
                path: { hops: 2, next_hop_interface: "TCP Client" },
            },
        });
        const ctx = {
            nodePathsByHash: {},
        };
        await PropagationNodesPage.methods.requestPathForNode.call(ctx, "abcd");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/destination/abcd/path", {
            params: { request: "1", timeout: 4 },
        });
        expect(ctx.nodePathsByHash.abcd).toEqual({ hops: 2, next_hop_interface: "TCP Client" });
    });

    it("sets preferred node from a pasted hash and turns off auto-select", async () => {
        const ctx = {
            config: { lxmf_preferred_propagation_node_auto_select: true },
            manualHashDraft: "",
            updateConfig: vi.fn().mockResolvedValue(true),
            requestPathForNode: vi.fn(),
            $t: (k) => k,
        };
        await PropagationNodesPage.methods.usePropagationNode.call(ctx, "<A39610C89D18BB48C73E429582423C24>");
        expect(ctx.updateConfig).toHaveBeenCalledWith({
            lxmf_preferred_propagation_node_destination_hash: "a39610c89d18bb48c73e429582423c24",
            lxmf_preferred_propagation_node_auto_select: false,
        });
        expect(ctx.manualHashDraft).toBe("a39610c89d18bb48c73e429582423c24");
        expect(ToastUtils.success).toHaveBeenCalledWith("tools.propagation_nodes.preferred_set");
        expect(ctx.requestPathForNode).toHaveBeenCalledWith("a39610c89d18bb48c73e429582423c24");
    });

    it("rejects an invalid preferred node hash", async () => {
        const ctx = {
            config: { lxmf_preferred_propagation_node_auto_select: false },
            updateConfig: vi.fn(),
            requestPathForNode: vi.fn(),
            $t: (k) => k,
        };
        await PropagationNodesPage.methods.usePropagationNode.call(ctx, "nope");
        expect(ctx.updateConfig).not.toHaveBeenCalled();
        expect(ToastUtils.error).toHaveBeenCalledWith("tools.propagation_nodes.invalid_hash");
    });

    it("normalizes a pasted hash in the draft field", () => {
        const ctx = { manualHashDraft: "" };
        const event = {
            clipboardData: { getData: () => "<a39610c89d18bb48c73e429582423c24>" },
            preventDefault: vi.fn(),
        };
        PropagationNodesPage.methods.onManualHashPaste.call(ctx, event);
        expect(event.preventDefault).toHaveBeenCalled();
        expect(ctx.manualHashDraft).toBe("a39610c89d18bb48c73e429582423c24");
    });

    it("clears preferred node and draft", async () => {
        const ctx = {
            manualHashDraft: "a39610c89d18bb48c73e429582423c24",
            updateConfig: vi.fn().mockResolvedValue(true),
            $t: (k) => k,
        };
        await PropagationNodesPage.methods.stopUsingPropagationNode.call(ctx);
        expect(ctx.updateConfig).toHaveBeenCalledWith({
            lxmf_preferred_propagation_node_destination_hash: null,
        });
        expect(ctx.manualHashDraft).toBe("");
        expect(ToastUtils.success).toHaveBeenCalledWith("tools.propagation_nodes.preferred_cleared");
    });
});
