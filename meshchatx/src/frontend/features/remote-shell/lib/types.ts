// SPDX-License-Identifier: 0BSD

export interface RemoteShellOutputChunk {
    seq?: number;
    text?: string;
    ts?: number;
}

export interface RemoteShellSession {
    id: string;
    name?: string;
    mode: string;
    status: string;
    destination?: string;
    listen_address?: string;
    last_command?: string;
    output_chunks?: RemoteShellOutputChunk[];
    output_text?: string;
    created_at?: string | number;
}

export interface RemoteShellLayoutState {
    selectedSessionId: string | null;
}

export interface RemoteShellTab {
    id: string;
    label: string;
    shortLabel?: string;
    icon: string;
}
