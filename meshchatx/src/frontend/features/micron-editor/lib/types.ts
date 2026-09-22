// SPDX-License-Identifier: 0BSD

export interface MicronTab {
    id: number;
    name: string;
    content: string;
}

export interface PageNodeItem {
    node_id: string;
    name: string;
    running?: boolean;
    destination_hash?: string;
}

export interface LastPublishedInfo {
    destinationHash: string;
    pagePath: string;
    pageName: string;
    serverName: string;
}
