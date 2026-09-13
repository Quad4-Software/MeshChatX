// SPDX-License-Identifier: 0BSD

export type RncpTabId = "send" | "fetch" | "listen";

export interface RncpSendResult {
    success: boolean;
    message: string;
    filePath?: string;
}

export interface RncpFetchResult {
    success: boolean;
    message: string;
    savedPath?: string;
}

export interface RncpListenResult {
    success: boolean;
    message: string;
}

export interface RncpReceiveEvent {
    status: string;
    saved_path?: string;
    error?: string;
}

export interface RncpStatus {
    receive_directory?: string | null;
    listening?: boolean;
    destination_hash?: string | null;
    allowed_hashes?: string[];
    fetch_allowed?: boolean;
    fetch_jail?: string | null;
    allow_overwrite?: boolean;
}

export interface RncpListenPrefs {
    listenAllowedHashes: string;
    listenFetchJail: string | null;
    listenFetchAllowed: boolean;
    listenAllowOverwrite: boolean;
}
