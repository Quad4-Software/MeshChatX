// SPDX-License-Identifier: 0BSD

export interface ArchiveItem {
    id: number | string;
    hash?: string;
    destination_hash: string;
    node_name: string;
    page_path: string;
    created_at?: string;
    content?: string | null;
    preview?: string;
    snippet?: string;
    [key: string]: unknown;
}

export interface ArchivePagination {
    page: number;
    limit: number;
    total_count: number;
    total_pages: number;
}

export interface NodeOption {
    hash: string;
    label: string;
}

export interface NomadRenderOptions {
    renderMarkdown: boolean;
    renderHtml: boolean;
    renderPlaintext: boolean;
    nomadDestinationHash: string | null;
    nomad_micron_wasm_use: boolean;
}

export interface ArchivesApiResponse {
    archives?: ArchiveItem[];
    pagination?: Partial<ArchivePagination>;
}

export interface ArchiveItemApiResponse {
    archive?: ArchiveItem;
}

export interface ArchiveRecrawlApiResponse {
    archive?: ArchiveItem;
}
