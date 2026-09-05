// SPDX-License-Identifier: 0BSD

export interface DocsStatus {
    status: "idle" | "extracting" | "error" | string;
    progress: number;
    last_error: string | null;
    has_docs: boolean;
    has_meshchatx_docs: boolean;
    has_bundled_docs?: boolean;
    has_user_docs?: boolean;
    versions: string[];
    current_version: string | null;
}

export interface DocItem {
    name?: string;
    path: string;
    title?: string;
    lang?: string;
    type?: string;
}

export interface DocSection {
    id: string;
    title: string;
    items: DocItem[];
}

export interface DocLanguage {
    code: string;
    name: string;
}

export interface MeshChatXDocsListResponse {
    docs?: DocItem[];
    sections?: DocSection[];
    languages?: DocLanguage[];
    default_language?: string;
    manifest_error?: string;
}

export interface DocContentResponse {
    html?: string;
    content?: string;
    type?: string;
}

export interface DocTocEntry {
    id: string;
    text: string;
    level: 2 | 3;
}

export interface SearchResultItem {
    path: string;
    title: string;
    source: string;
    snippet: string;
}

export type DocsActiveTab = "meshchatx" | "reticulum";
