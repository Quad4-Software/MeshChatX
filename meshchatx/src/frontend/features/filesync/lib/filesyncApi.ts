// SPDX-License-Identifier: 0BSD

import type {
    AclRules,
    FilesyncDirectoryEntry,
    FilesyncPeer,
    FilesyncRemoteFile,
    FilesyncStatus,
    FilesyncTreeEntry,
} from "./types.js";

type WindowApi = {
    get: (
        url: string,
        config?: { params?: Record<string, unknown>; responseType?: string }
    ) => Promise<{ data?: unknown }>;
    post: (url: string, body?: unknown, config?: { responseType?: string }) => Promise<{ data?: unknown }>;
    patch: (url: string, body?: unknown) => Promise<{ data?: unknown }>;
    delete: (url: string, config?: { data?: unknown }) => Promise<{ data?: unknown }>;
};

function getApi(): WindowApi {
    const api = (window as unknown as { api?: WindowApi }).api;
    if (!api) {
        throw new Error("window.api is not available");
    }
    return api;
}

export async function fetchFilesyncStatus(): Promise<FilesyncStatus> {
    const res = await getApi().get("/api/v1/filesync/status");
    return (res.data || {}) as FilesyncStatus;
}

export async function fetchFilesyncPeers(): Promise<FilesyncPeer[]> {
    const res = await getApi().get("/api/v1/filesync/peers");
    const data = (res.data || {}) as { peers?: FilesyncPeer[] };
    return Array.isArray(data.peers) ? data.peers : [];
}

export async function fetchFilesyncAcl(): Promise<{ enforce: boolean; rules: AclRules }> {
    const res = await getApi().get("/api/v1/filesync/acl");
    const data = (res.data || {}) as { enforce?: boolean; rules?: AclRules };
    return {
        enforce: Boolean(data.enforce),
        rules: data.rules || {},
    };
}

export async function updateFilesyncSettings(payload: {
    sync_directory?: string;
    monitor?: boolean;
    announce_interval?: number;
}): Promise<void> {
    await getApi().patch("/api/v1/filesync/settings", payload);
}

export async function startFilesyncService(payload: {
    sync_directory?: string;
    monitor?: boolean;
    announce_interval?: number;
}): Promise<void> {
    await getApi().post("/api/v1/filesync/start", payload);
}

export async function stopFilesyncService(): Promise<void> {
    await getApi().post("/api/v1/filesync/stop", {});
}

export async function announceFilesyncNow(): Promise<void> {
    await getApi().post("/api/v1/filesync/announce", {});
}

export async function connectFilesyncPeer(identityHash: string): Promise<void> {
    await getApi().post("/api/v1/filesync/connect", {
        identity_hash: identityHash,
    });
}

export async function disconnectFilesyncPeer(peerId: string): Promise<void> {
    await getApi().post("/api/v1/filesync/disconnect", {
        peer_id: peerId,
    });
}

export async function browseFilesyncPeer(peerId: string): Promise<FilesyncRemoteFile[]> {
    const res = await getApi().post("/api/v1/filesync/browse", {
        peer_id: peerId,
    });
    const data = (res.data || {}) as { files?: FilesyncRemoteFile[] };
    return Array.isArray(data.files) ? data.files : [];
}

export async function downloadFilesyncRemoteFile(peerId: string, path: string): Promise<void> {
    await getApi().post("/api/v1/filesync/download", {
        peer_id: peerId,
        path,
    });
}

export async function grantFilesyncAcl(payload: {
    identity_hash?: string;
    perms?: string[];
    enforce?: boolean;
}): Promise<void> {
    await getApi().post("/api/v1/filesync/acl", payload);
}

export async function fetchSharedDirectorySuggestion(): Promise<string> {
    const res = await getApi().get("/api/v1/filesync/shared-directory-suggestion");
    const data = (res.data || {}) as { path?: string };
    return String(data.path || "").trim();
}

export async function fetchFilesyncTree(path?: string): Promise<{
    entries: FilesyncTreeEntry[];
    current: string;
    parent: string | null;
}> {
    const params: Record<string, unknown> = {};
    if (path) {
        params.path = path;
    }
    const res = await getApi().get("/api/v1/filesync/tree", { params });
    const data = (res.data || {}) as {
        entries?: FilesyncTreeEntry[];
        current?: string;
        parent?: string | null;
    };
    return {
        entries: Array.isArray(data.entries) ? data.entries : [],
        current: data.current != null ? String(data.current) : "",
        parent: data.parent === undefined ? null : data.parent,
    };
}

export async function uploadFilesyncFile(formData: FormData): Promise<void> {
    await getApi().post("/api/v1/filesync/upload", formData);
}

export async function mkdirFilesyncFolder(path: string): Promise<void> {
    await getApi().post("/api/v1/filesync/mkdir", { path });
}

export async function fetchFilesyncContent(path: string): Promise<unknown> {
    return await getApi().get("/api/v1/filesync/content", {
        params: { path },
        responseType: "blob",
    });
}

export async function deleteFilesyncEntry(path: string): Promise<void> {
    await getApi().delete("/api/v1/filesync/entry", { data: { path } });
}

export async function fetchFilesyncDirectories(path?: string): Promise<{
    root: string;
    current: string;
    parent: string | null;
    directories: FilesyncDirectoryEntry[];
}> {
    const url = path ? `/api/v1/filesync/directories?path=${encodeURIComponent(path)}` : "/api/v1/filesync/directories";
    const res = await getApi().get(url);
    const data = (res.data || {}) as {
        root?: string;
        current?: string;
        parent?: string | null;
        directories?: FilesyncDirectoryEntry[];
    };
    return {
        root: data.root || "",
        current: data.current || "",
        parent: data.parent || null,
        directories: Array.isArray(data.directories) ? data.directories : [],
    };
}

export async function createFilesyncDirectory(parent: string, name: string): Promise<{ path?: string }> {
    const res = await getApi().post("/api/v1/filesync/directories", {
        parent,
        name,
    });
    return (res.data || {}) as { path?: string };
}
