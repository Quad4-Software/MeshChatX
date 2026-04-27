const destinationPath = (hash) => `/api/v1/destination/${hash}/path`;

/**
 * @param {import("axios").AxiosInstance} api
 * @param {string} hash
 * @param {{ request?: "0" | "1" | boolean, timeout?: number } & Record<string, string | number | boolean | undefined>} [params]
 */
export function getDestinationPath(api, hash, params) {
    const q = { ...params };
    if (q.request === true) {
        q.request = "1";
    } else if (q.request === false) {
        q.request = "0";
    }
    return api.get(destinationPath(hash), { params: q });
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
        const res = await getDestinationPath(api, hash, {
            request: "1",
            timeout: forceTimeout,
        });
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
