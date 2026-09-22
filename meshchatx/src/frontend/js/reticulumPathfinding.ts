export type PeerPathSnapshot = {
    path: object | null;
    path_stale: boolean;
    path_unresponsive: boolean;
};

export type PathFinderMode = "quick" | "force" | "drop_then_request";

export type PathfindingApi = {
    get: (path: string, config?: { params?: Record<string, unknown> }) => Promise<{ data?: unknown }>;
    post: (path: string, data?: unknown, config?: { params?: Record<string, unknown> }) => Promise<{ data?: any }>;
};

export type PathFinderOptions = {
    forceTimeout?: number;
    onDropPathError?: (e: unknown) => void;
};

export type PathFinderResult = {
    ok: true;
    path: object | null;
};

const destinationPath = (hash: string): string => `/api/v1/destination/${hash}/path`;

export function normalizePathSnapshot(data: unknown): PeerPathSnapshot {
    if (!data || typeof data !== "object") {
        return { path: null, path_stale: true, path_unresponsive: false };
    }
    const row = data as {
        path?: object | null;
        path_stale?: boolean;
        path_unresponsive?: boolean;
    };
    const path = row.path ?? null;
    return {
        path,
        path_stale: path == null ? true : Boolean(row.path_stale),
        path_unresponsive: Boolean(row.path_unresponsive),
    };
}

export function pathNeedsRefresh(snapshot: PeerPathSnapshot | null | undefined): boolean {
    if (!snapshot) {
        return true;
    }
    if (!snapshot.path) {
        return true;
    }
    if (snapshot.path_stale) {
        return true;
    }
    if (snapshot.path_unresponsive) {
        return true;
    }
    return false;
}

export function pathIsReady(snapshot: PeerPathSnapshot | null | undefined): boolean {
    return Boolean(snapshot?.path && !snapshot.path_stale && !snapshot.path_unresponsive);
}

export async function fetchPeerPathSnapshot(api: PathfindingApi, hash: string): Promise<PeerPathSnapshot> {
    const res = await getDestinationPath(api, hash, {});
    return normalizePathSnapshot(res.data);
}

/** Request a mesh path refresh only when the current snapshot is missing or stale. */
export async function warmPathIfNeeded(
    api: PathfindingApi,
    hash: string,
    snapshot: PeerPathSnapshot | null | undefined
): Promise<{ requested: boolean }> {
    if (!pathNeedsRefresh(snapshot)) {
        return { requested: false };
    }
    await postRequestPath(api, hash);
    return { requested: true };
}

/** Snapshot-only. Waiting for a path uses postDestinationPath. */
export function getDestinationPath(
    api: PathfindingApi,
    hash: string,
    params?: Record<string, string | number | boolean | undefined>
) {
    const q: Record<string, string | number | boolean | undefined> = { ...params };
    delete q.request;
    return api.get(destinationPath(hash), { params: q });
}

export function postDestinationPath(api: PathfindingApi, hash: string, options?: { timeout?: number }) {
    const timeout = options?.timeout;
    const params = timeout == null ? {} : { timeout };
    return api.post(destinationPath(hash), {}, { params });
}

export function postRequestPath(api: PathfindingApi, hash: string) {
    return api.post(`/api/v1/destination/${hash}/request-path`);
}

export function postDropPath(api: PathfindingApi, hash: string) {
    return api.post(`/api/v1/destination/${hash}/drop-path`);
}

export async function runDestinationPathFinder(
    api: PathfindingApi,
    hash: string,
    mode: PathFinderMode | string,
    options?: PathFinderOptions
): Promise<PathFinderResult> {
    const forceTimeout = options?.forceTimeout ?? 15;
    if (mode === "quick") {
        await postRequestPath(api, hash);
        return { ok: true, path: null };
    }
    if (mode === "force") {
        const res = await postDestinationPath(api, hash, { timeout: forceTimeout });
        return { ok: true, path: res.data?.path ?? null };
    }
    if (mode === "drop_then_request") {
        try {
            await postDropPath(api, hash);
        } catch (e) {
            if (options?.onDropPathError) {
                options.onDropPathError(e);
            } else {
                console.warn("drop-path failed (continuing)", e);
            }
        }
        await postRequestPath(api, hash);
        return { ok: true, path: null };
    }
    throw new Error(`unknown path finder mode: ${mode}`);
}
