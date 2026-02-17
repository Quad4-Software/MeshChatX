import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe("App propagation sync metrics", () => {
    const axiosMock = {
        get: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        globalThis.axios = axiosMock;
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("shows detailed sync toast with stored, confirmations and hidden counts", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/sync") {
                return Promise.resolve({ data: { message: "Sync is starting" } });
            }
            if (url === "/api/v1/lxmf/propagation-node/status") {
                return Promise.resolve({
                    data: {
                        propagation_node_status: {
                            state: "complete",
                            messages_received: 8,
                            messages_stored: 3,
                            delivery_confirmations: 2,
                            messages_hidden: 3,
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const ctx = {
            propagationNodeStatus: null,
            get isSyncingPropagationNode() {
                return [
                    "path_requested",
                    "link_establishing",
                    "link_established",
                    "request_sent",
                    "receiving",
                    "response_received",
                ].includes(this.propagationNodeStatus?.state);
            },
            async updatePropagationNodeStatus() {
                return App.methods.updatePropagationNodeStatus.call(this);
            },
            async stopSyncingPropagationNode() {},
            $t(key, params = {}) {
                if (key === "app.sync_complete") {
                    return `Sync complete. ${params.count} messages received.`;
                }
                if (key === "app.sync_error") {
                    return `Sync error: ${params.status}`;
                }
                if (key === "app.sync_error_generic") {
                    return "Sync failed";
                }
                if (key === "app.stop_sync_confirm") {
                    return "Stop syncing?";
                }
                return key;
            },
        };

        await App.methods.syncPropagationNode.call(ctx);
        vi.advanceTimersByTime(600);

        expect(ToastUtils.success).toHaveBeenCalledWith(
            "Sync complete. 8 messages received. (3 stored, 2 confirmations, 3 hidden)"
        );
        expect(ToastUtils.error).not.toHaveBeenCalled();
    });
});
