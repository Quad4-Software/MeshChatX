const destinationPath = (hash) => `/api/v1/destination/${hash}/path`;

/**
 * @typedef {{ path: object | null, path_stale: boolean, path_unresponsive: boolean }} PeerPathSnapshot
 */

/**
 * @param {unknown} data
 * @returns {PeerPathSnapshot}
 */
export function normalizePathSnapshot(data) {
    if (!data || typeof data !== "object") {
        return { path: null, path_stale: true, path_unresponsive: false };
    }
    const row = /** @type {{ path?: object | null, path_stale?: boolean, path_unresponsive?: boolean }} */ data;
    const path = row.path ?? null;
    return {
        path,
        path_stale: path == null ? true : Boolean(row.path_stale),
        path_unresponsive: Boolean(row.path_unresponsive),
    };
}

/**
 * @param {PeerPathSnapshot | null | undefined} snapshot
 */
export function pathNeedsRefresh(snapshot) {
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

/**
 * @param {PeerPathSnapshot | null | undefined} snapshot
 */
export function pathIsReady(snapshot) {
    return Boolean(snapshot?.path && !snapshot.path_stale && !snapshot.path_unresponsive);
}

/**
 * @param {import("axios").AxiosInstance} api
 * @param {string} hash
 * @returns {Promise<PeerPathSnapshot>}
 */
export async function fetchPeerPathSnapshot(api, hash) {
    const res = await getDestinationPath(api, hash, {});
    return normalizePathSnapshot(res.data);
}

/**
 * Request a mesh path refresh only when the current snapshot is missing or stale.
 *
 * @param {import("axios").AxiosInstance} api
 * @param {string} hash
 * @param {PeerPathSnapshot | null | undefined} snapshot
 * @returns {Promise<{ requested: boolean }>}
 */
export async function warmPathIfNeeded(api, hash, snapshot) {
    if (!pathNeedsRefresh(snapshot)) {
        return { requested: false };
    }
    await postRequestPath(api, hash);
    return { requested: true };
}

/**
 * Snapshot-only. Waiting for a path uses postDestinationPath.
 *
 * @param {import("axios").AxiosInstance} api
 * @param {string} hash
 * @param {Record<string, string | number | boolean | undefined>} [params]
 */
export function getDestinationPath(api, hash, params) {
    const q: any = { ...params };
    delete q.request;
    return api.get(destinationPath(hash), { params: q });
}

/**
 * @param {import("axios").AxiosInstance} api
 * @param {string} hash
 * @param {{ timeout?: number }} [options]
 */
export function postDestinationPath(api, hash, options) {
    const timeout = options?.timeout;
    const params = timeout == null ? {} : { timeout };
    return api.post(destinationPath(hash), {}, { params });
}

export function postRequestPath(api, hash) {
    return api.post(`/api/v1/destination/${hash}/request-path`);
}

export function postDropPath(api, hash) {
    return api.post(`/api/v1/destination/${hash}/drop-path`);
}

/**
 * @typedef {"quick" | "force" | "drop_then_request"} PathFinderMode
 */

/**
 * @param {import("axios").AxiosInstance} api
 * @param {string} hash
 * @param {PathFinderMode} mode
 * @param {{ forceTimeout?: number, onDropPathError?: (e: unknown) => void }} [options]
 */
export async function runDestinationPathFinder(api, hash, mode, options) {
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
