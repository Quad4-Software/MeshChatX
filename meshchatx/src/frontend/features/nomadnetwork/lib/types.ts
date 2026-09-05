// SPDX-License-Identifier: 0BSD

export interface NomadTab {
    id: number;
    destinationHash: string;
    initialPath: string | null;
    path: string | null;
    title: string | null;
    private: boolean;
}

export interface NomadNode {
    destination_hash: string;
    identity_hash?: string;
    display_name?: string;
    custom_display_name?: string | null;
    updated_at?: string;
    aspect?: string;
    hops?: number;
    [key: string]: unknown;
}

export interface NomadFavourite {
    destination_hash: string;
    display_name?: string;
    custom_display_name?: string | null;
    aspect?: string;
    identify_on_connect?: boolean;
    [key: string]: unknown;
}

export interface NomadSection {
    id: string;
    name: string;
    collapsed: boolean;
    favourites?: NomadFavourite[];
}

export interface NomadPageArchive {
    id: number | string;
    hash: string;
    created_at: string;
    size?: number;
    destination_hash?: string;
    path?: string;
}

export interface NomadNavigateEvent {
    kind?: string;
    url?: string;
    fields?: Record<string, string>;
    fieldSpec?: string;
    button?: number;
    ctrlKey?: boolean;
    metaKey?: boolean;
}

export interface NomadContextMenuState {
    show: boolean;
    justOpened: boolean;
    x: number;
    y: number;
    tabId: number | null;
}

export interface NomadPageRendererChip {
    label: string;
    popoverVariant?: string;
    micronGoRelease?: string;
    tooltipBody?: string;
}

export interface NomadDestinationPath {
    hops: number;
    interface?: string;
    interface_name?: string;
    next_hop?: string;
    next_hop_interface?: string;
    [key: string]: unknown;
}

export interface NomadPageStats {
    duration: string;
    sizeLabel: string;
}
