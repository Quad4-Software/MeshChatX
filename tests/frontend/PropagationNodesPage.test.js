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
        post: vi.fn(),
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
        };

        await PropagationNodesPage.methods.useLocalPropagationNode.call(ctx);
        expect(ctx.usePropagationNode).toHaveBeenCalledWith("local-node");
    });

    it("debounces propagation transfer limit save", async () => {
        const ctx = {
            config: {
                lxmf_propagation_transfer_limit_in_bytes: 123456,
            },
            saveTimeouts: {
                propagationLimit: null,
            },
            updateConfig: vi.fn().mockResolvedValue(undefined),
        };

        await PropagationNodesPage.methods.onPropagationTransferLimitChange.call(ctx);
        expect(ctx.updateConfig).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(500);
        expect(ctx.updateConfig).toHaveBeenCalledWith({
            lxmf_propagation_transfer_limit_in_bytes: 123456,
        });
    });

    it("stops and restarts local node via API", async () => {
        axiosMock.post.mockResolvedValue({ data: {} });
        const ctx = {
            getConfig: vi.fn().mockResolvedValue(undefined),
            loadPropagationNodes: vi.fn().mockResolvedValue(undefined),
            $t: (k) => k,
        };

        await PropagationNodesPage.methods.stopLocalPropagationNode.call(ctx);
        await PropagationNodesPage.methods.restartLocalPropagationNode.call(ctx);

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/lxmf/propagation-node/stop");
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/lxmf/propagation-node/restart");
        expect(ToastUtils.success).toHaveBeenCalledTimes(2);
    });
});
