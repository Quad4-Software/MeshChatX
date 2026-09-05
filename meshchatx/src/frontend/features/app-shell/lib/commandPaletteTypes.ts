// SPDX-License-Identifier: 0BSD

export interface PeerAnnounce {
    destination_hash: string;
    display_name?: string;
    custom_display_name?: string;
    lxmf_user_icon?: {
        icon_name?: string;
        foreground_colour?: string;
        background_colour?: string;
    };
}

export interface Contact {
    id: number | string;
    name: string;
    remote_identity_hash: string;
    custom_image?: string;
}

export interface ResultItem {
    id: string;
    title: string;
    description: string;
    icon: string;
    type: "navigation" | "action" | "peer" | "contact";
    route?: { name?: string; path?: string; params?: Record<string, unknown>; query?: Record<string, unknown> };
    action?: string;
    iconForeground?: string;
    iconBackground?: string;
    peer?: PeerAnnounce;
    contact?: Contact;
}
