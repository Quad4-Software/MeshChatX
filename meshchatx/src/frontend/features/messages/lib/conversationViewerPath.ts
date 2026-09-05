// SPDX-License-Identifier: 0BSD

import {
    fetchPeerPathSnapshot,
    normalizePathSnapshot,
    pathNeedsRefresh,
    runDestinationPathFinder,
    warmPathIfNeeded,
} from "../../../js/reticulumPathfinding.js";
import { isDestinationHash } from "../../../js/meshValidate.js";
import type { ApiClient } from "../../../js/apiClient.js";
import type { ViewerPathSnapshot } from "./conversationViewerCtx.js";

export type PeerNetworkInfo = {
    path: ViewerPathSnapshot;
    stampInfo: Record<string, unknown> | null;
    signalMetrics: Record<string, unknown> | null;
};

export async function loadPeerNetworkInfo(api: ApiClient, hash: string, warm: boolean): Promise<PeerNetworkInfo> {
    let path = (await fetchPeerPathSnapshot(api, hash)) as ViewerPathSnapshot;
    if (warm) {
        const result = await warmPathIfNeeded(api, hash, path as never);
        if (result?.requested) {
            path = (await fetchPeerPathSnapshot(api, hash)) as ViewerPathSnapshot;
        }
    }
    const [stamp, signal] = await Promise.allSettled([
        api.get(`/api/v1/destination/${hash}/lxmf-stamp-info`),
        api.get(`/api/v1/destination/${hash}/signal-metrics`),
    ]);
    return {
        path: (path || normalizePathSnapshot(null)) as ViewerPathSnapshot,
        stampInfo:
            stamp.status === "fulfilled"
                ? (((stamp.value.data as { lxmf_stamp_info?: Record<string, unknown> })?.lxmf_stamp_info as Record<
                      string,
                      unknown
                  >) ?? null)
                : null,
        signalMetrics:
            signal.status === "fulfilled"
                ? (((signal.value.data as { signal_metrics?: Record<string, unknown> })?.signal_metrics as Record<
                      string,
                      unknown
                  >) ?? null)
                : null,
    };
}

export async function warmOutboundPath(
    api: ApiClient,
    destinationHash: string,
    deliveryMethod: string | null,
    current: ViewerPathSnapshot | null,
    propagationHash?: unknown
): Promise<void> {
    if (deliveryMethod === "propagated") {
        if (typeof propagationHash === "string" && isDestinationHash(propagationHash)) {
            await warmPathIfNeeded(api, propagationHash, null);
        }
        return;
    }
    await warmPathIfNeeded(api, destinationHash, current as never);
}

export function peerPathNeedsRefresh(snapshot: ViewerPathSnapshot | null): boolean {
    return pathNeedsRefresh(snapshot as never);
}

export async function runPeerPathAction(
    api: ApiClient,
    hash: string,
    action: "quick" | "force" | "drop_then_request"
): Promise<ViewerPathSnapshot | null> {
    if (action === "force") {
        const result = await runDestinationPathFinder(api, hash, action, { forceTimeout: 15 });
        if (result?.path) {
            return normalizePathSnapshot({
                path: result.path,
                path_stale: false,
                path_unresponsive: false,
            }) as ViewerPathSnapshot;
        }
    } else {
        await runDestinationPathFinder(api, hash, action, {
            onDropPathError: (error: unknown) => console.warn("drop-path failed", error),
        });
    }
    return (await fetchPeerPathSnapshot(api, hash)) as ViewerPathSnapshot;
}
