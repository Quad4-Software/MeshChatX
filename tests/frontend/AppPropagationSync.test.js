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
        config: {
            lxmf_preferred_propagation_node_destination_hash: "deadbeef",
        },
        propagationNodeStatus: null,
        _propagationSyncPollTimer: null,
        _isPropagationSyncPolling: false,
        userInitiatedPropagationSync: false,
        propagationSyncLiveToastMessage: App.methods.propagationSyncLiveToastMessage,
        propagationSyncStatusLabel: App.methods.propagationSyncStatusLabel,
        get isSyncingPropagationNode() {
            if (!this.userInitiatedPropagationSync) {
                return false;
            }
            return syncingStates.includes(this.propagationNodeStatus?.state);
        },
        async updatePropagationNodeStatus() {
            try {
                const response = await axiosMock.get("/api/v1/lxmf/propagation-node/status");
                this.propagationNodeStatus = response.data.propagation_node_status;
                const state = this.propagationNodeStatus?.state;
                if (this.userInitiatedPropagationSync && state && !syncingStates.includes(state)) {
                    this.userInitiatedPropagationSync = false;
                }
            } catch {
                // ignore
            }
        },
        async stopSyncingPropagationNode() {
            this.userInitiatedPropagationSync = false;
        },
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
        post: vi.fn(),
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
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/sync") {
                return Promise.resolve({ data: { message: "Sync is starting" } });
            }
            return Promise.resolve({ data: { message: "ok" } });
        });
        axiosMock.get.mockImplementation((url) => {
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
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/lxmf/propagation-node/sync");
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/destination/deadbeef/request-path");
        expect(ToastUtils.error).not.toHaveBeenCalled();
    });

    it("polls status while syncing and updates live loading toast", async () => {
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/sync") {
                return Promise.resolve({ data: { message: "Sync is starting" } });
            }
            return Promise.resolve({ data: { message: "ok" } });
        });
        let statusCalls = 0;
        axiosMock.get.mockImplementation((url) => {
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
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/sync") {
                return Promise.resolve({ data: { message: "Sync is starting" } });
            }
            return Promise.resolve({ data: { message: "ok" } });
        });
        axiosMock.get.mockImplementation((url) => {
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

    it("still starts sync when request-path fails (stale CSRF / brief offline after background)", async () => {
        // Oracle: request-path is best-effort priming. The /sync POST already
        // requests a path server-side. A CSRF or network failure on the POST
        // must not abort the user-initiated sync (common after a backgrounded tab).
        let syncCalled = false;
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/sync") {
                syncCalled = true;
                return Promise.resolve({ data: { message: "Sync is starting" } });
            }
            return Promise.reject(
                Object.assign(new Error("HTTP 403"), {
                    response: { status: 403, data: { error: "Invalid or missing CSRF token" } },
                })
            );
        });
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/status") {
                return Promise.resolve({
                    data: {
                        propagation_node_status: {
                            state: "complete",
                            progress: 100,
                            messages_received: 1,
                            messages_stored: 1,
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

        expect(syncCalled).toBe(true);
        expect(ToastUtils.success).toHaveBeenCalled();
        expect(ToastUtils.error).not.toHaveBeenCalled();
    });

    it("clears stuck userInitiatedPropagationSync when status returns idle after background", async () => {
        // Oracle: after a backgrounded tab, chrome can still show a prior sync
        // as running. A status poll that sees idle/complete must clear the flag
        // so the next Sync Messages click starts a new sync instead of stop-confirm.
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/propagation-node/status") {
                return Promise.resolve({
                    data: {
                        propagation_node_status: {
                            state: "idle",
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
        ctx.userInitiatedPropagationSync = true;
        ctx.propagationNodeStatus = { state: "path_requested", progress: 5 };
        expect(ctx.isSyncingPropagationNode).toBe(true);

        await App.methods.updatePropagationNodeStatus.call(ctx);

        expect(ctx.userInitiatedPropagationSync).toBe(false);
        expect(ctx.propagationNodeStatus.state).toBe("idle");
        expect(ctx.isSyncingPropagationNode).toBe(false);
    });
});
