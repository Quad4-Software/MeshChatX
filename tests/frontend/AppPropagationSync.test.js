import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

const syncingStates = [
    "path_requested",
    "link_establishing",
    "link_established",
    "request_sent",
    "receiving",
    "response_received",
];

function makeSyncContext(axiosMock, tOverrides = {}) {
    return {
        propagationNodeStatus: null,
        _propagationSyncPollTimer: null,
        propagationSyncLiveToastMessage: App.methods.propagationSyncLiveToastMessage,
        propagationSyncStatusLabel: App.methods.propagationSyncStatusLabel,
        get isSyncingPropagationNode() {
            return syncingStates.includes(this.propagationNodeStatus?.state);
        },
        async updatePropagationNodeStatus() {
            try {
                const response = await axiosMock.get("/api/v1/lxmf/propagation-node/status");
                this.propagationNodeStatus = response.data.propagation_node_status;
            } catch {
                // ignore
            }
        },
        async stopSyncingPropagationNode() {},
        $t(key, params = {}) {
            if (tOverrides[key]) {
                return tOverrides[key](params);
            }
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
            if (key === "app.propagation_sync_live") {
                return `Syncing: ${params.status} (${params.progress}%)`;
            }
            if (key.startsWith("app.propagation_sync_state.")) {
                const sub = key.slice("app.propagation_sync_state.".length);
                const labels = {
                    path_requested: "Requesting path",
                    receiving: "Receiving messages",
                    complete: "Complete",
                    idle: "Idle",
                    no_path: "No path to node",
                    unknown: "Unknown state",
                };
                return labels[sub] ?? sub;
            }
            return key;
        },
    };
}

describe("App propagation sync", () => {
    const axiosMock = {
        get: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        globalThis.api = axiosMock;
        window.api = axiosMock;
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("shows detailed success toast with stored, confirmations and hidden counts", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/sync") {
                return Promise.resolve({ data: { message: "Sync is starting" } });
            }
            if (url === "/api/v1/lxmf/propagation-node/status") {
                return Promise.resolve({
                    data: {
                        propagation_node_status: {
                            state: "complete",
                            progress: 100,
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

        const ctx = makeSyncContext(axiosMock);

        await App.methods.syncPropagationNode.call(ctx);
        await vi.runOnlyPendingTimersAsync();

        expect(ToastUtils.loading).not.toHaveBeenCalled();
        expect(ToastUtils.dismiss).toHaveBeenCalledWith("propagation-sync-status");
        expect(ToastUtils.success).toHaveBeenCalledWith(
            "Sync complete. 8 messages received. (3 stored, 2 confirmations, 3 hidden)"
        );
        expect(ToastUtils.error).not.toHaveBeenCalled();
    });

    it("polls status while syncing and updates live loading toast", async () => {
        let statusCalls = 0;
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/sync") {
                return Promise.resolve({ data: { message: "Sync is starting" } });
            }
            if (url === "/api/v1/lxmf/propagation-node/status") {
                statusCalls += 1;
                if (statusCalls < 3) {
                    return Promise.resolve({
                        data: {
                            propagation_node_status: {
                                state: "path_requested",
                                progress: 12,
                                messages_received: 0,
                                messages_stored: 0,
                                delivery_confirmations: 0,
                                messages_hidden: 0,
                            },
                        },
                    });
                }
                return Promise.resolve({
                    data: {
                        propagation_node_status: {
                            state: "complete",
                            progress: 100,
                            messages_received: 2,
                            messages_stored: 1,
                            delivery_confirmations: 1,
                            messages_hidden: 0,
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const ctx = makeSyncContext(axiosMock);

        const syncPromise = App.methods.syncPropagationNode.call(ctx);
        await vi.runOnlyPendingTimersAsync();
        vi.advanceTimersByTime(500);
        await vi.runOnlyPendingTimersAsync();
        await syncPromise;

        expect(statusCalls).toBeGreaterThanOrEqual(3);
        expect(ToastUtils.loading).toHaveBeenCalledWith("Syncing: Requesting path (12%)", 0, "propagation-sync-status");
        expect(ToastUtils.dismiss).toHaveBeenCalledWith("propagation-sync-status");
        expect(ToastUtils.success).toHaveBeenCalled();
    });

    it("uses translated status in error toast when sync ends in a failure state", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/sync") {
                return Promise.resolve({ data: { message: "Sync is starting" } });
            }
            if (url === "/api/v1/lxmf/propagation-node/status") {
                return Promise.resolve({
                    data: {
                        propagation_node_status: {
                            state: "no_path",
                            progress: 0,
                            messages_received: 0,
                            messages_stored: 0,
                            delivery_confirmations: 0,
                            messages_hidden: 0,
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const ctx = makeSyncContext(axiosMock);

        await App.methods.syncPropagationNode.call(ctx);
        await vi.runOnlyPendingTimersAsync();

        expect(ToastUtils.error).toHaveBeenCalledWith("Sync error: No path to node");
        expect(ToastUtils.success).not.toHaveBeenCalled();
    });
});
