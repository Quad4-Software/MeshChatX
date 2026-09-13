// SPDX-License-Identifier: 0BSD

export type FilesyncTabId = "folder" | "devices" | "files" | "remote" | "sharing";

export interface FilesyncStatus {
    running: boolean;
    peers?: number;
    files?: number;
    destination_hash?: string | null;
    sync_directory?: string;
    storage_directory?: string;
    monitor?: boolean;
    announce_interval?: number;
}

export interface FilesyncPeer {
    peer_id: string;
    destination_hash?: string;
    status?: number | string | boolean;
}

export type FilesyncRemoteFile = {
    path?: string;
    size?: number;
    name?: string;
};

export interface FilesyncTreeEntry {
    name: string;
    path: string;
    type: "file" | "dir";
    size?: number;
}

export interface FilesyncDirectoryEntry {
    name: string;
    path: string;
}

export interface AclRules {
    read?: string[];
    write?: string[];
    delete?: string[];
    [key: string]: string[] | undefined;
}

export interface AclRow {
    hash: string;
    permsLabel: string;
}

export type FilesyncProgressPayload = Record<string, unknown> | string;
