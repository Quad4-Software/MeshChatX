// SPDX-License-Identifier: 0BSD

export type BlocklistScope = "everyone" | "contacts" | "non_contacts";

export type BlocklistMatchMode = "substring" | "regex";

export type BlocklistEntry = {
    id: string;
    enabled: boolean;
    text: string;
    match_mode: BlocklistMatchMode;
};

export type BlocklistConfig = {
    scope: BlocklistScope;
    match_peer_fields: boolean;
    match_message: boolean;
    entries: BlocklistEntry[];
};

export type MessageBlocklistApiResponse = {
    enabled?: boolean;
    blocklist?: Partial<BlocklistConfig> & {
        entries?: Partial<BlocklistEntry>[];
    };
    message?: string;
};

export type MessageBlocklistImportPayload = {
    document: unknown;
    merge: boolean;
};

export type MessageBlocklistSavePayload = {
    enabled: boolean;
    blocklist: BlocklistConfig;
};
