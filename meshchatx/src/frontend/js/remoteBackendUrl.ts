/**
 * Normalize a MeshChatX remote backend URL for the Android shell.
 * Empty string means the on-device local backend.
 */

const LOCAL_BACKEND_URL = "https://127.0.0.1:8000";

/** Normalized origin without trailing slash, or null for local. */
export function normalizeRemoteBackendUrl(raw: string | null | undefined): string | null {
    if (raw == null) {
        return null;
    }
    const trimmed = String(raw).trim();
    if (!trimmed) {
        return null;
    }
    let url: URL;
    try {
        url = new URL(trimmed);
    } catch {
        return null;
    }
    const scheme = url.protocol.replace(/:$/, "").toLowerCase();
    if (scheme !== "http" && scheme !== "https") {
        return null;
    }
    if (url.username || url.password) {
        return null;
    }
    if (!url.hostname) {
        return null;
    }
    let out = `${scheme}://${url.hostname.toLowerCase()}`;
    if (url.port) {
        out += `:${url.port}`;
    }
    let path = url.pathname || "";
    if (path && path !== "/") {
        while (path.length > 1 && path.endsWith("/")) {
            path = path.slice(0, -1);
        }
        out += path;
    }
    return out;
}

export function isValidRemoteBackendUrl(raw: string | null | undefined): boolean {
    if (raw == null) {
        return true;
    }
    const trimmed = String(raw).trim();
    if (!trimmed) {
        return true;
    }
    return normalizeRemoteBackendUrl(trimmed) != null;
}

export function resolveEffectiveBackendUrl(storedRemote: string | null | undefined): string {
    return normalizeRemoteBackendUrl(storedRemote) || LOCAL_BACKEND_URL;
}

export { LOCAL_BACKEND_URL };
