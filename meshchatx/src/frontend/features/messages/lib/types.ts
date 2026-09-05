// SPDX-License-Identifier: 0BSD

/**
 * Shared Messages page types. Fields stay optional and Record-friendly to match Vue usage.
 */

export type LxmfUserIconInfo = {
    icon_name?: string;
    foreground_colour?: string;
    background_colour?: string;
};

export type Peer = {
    destination_hash?: string;
    display_name?: string | null;
    custom_display_name?: string | null;
    contact_image?: string | null;
    lxmf_user_icon?: LxmfUserIconInfo | null;
    is_tracking?: boolean;
    is_unread?: boolean;
    updated_at?: string | null;
    [key: string]: unknown;
};

export type Conversation = {
    destination_hash?: string;
    display_name?: string | null;
    custom_display_name?: string | null;
    contact_image?: string | null;
    lxmf_user_icon?: LxmfUserIconInfo | null;
    is_unread?: boolean;
    is_tracking?: boolean;
    failed_messages_count?: number;
    has_attachments?: boolean;
    latest_message_preview?: string | null;
    latest_message_title?: string | null;
    latest_message_created_at?: number | null;
    updated_at?: string | null;
    is_contact?: boolean;
    _lastKnownState?: string | null;
    [key: string]: unknown;
};

/** Loose chat row / message carrier used by viewers and list helpers. */
export type ChatItem = {
    lxmf_message?: Record<string, unknown>;
    is_outbound?: boolean;
    [key: string]: unknown;
};

export type Pane = {
    id: number;
    peer: Peer | null;
};

export type Folder = {
    id?: number | string | null;
    name?: string | null;
    [key: string]: unknown;
};

/** Config slice read by MessagesPage (not the full backend config object). */
export type MessagesConfig = {
    messages_multi_pane_enabled?: boolean;
    messages_sidebar_position?: string;
    lxmf_address_hash?: string;
    do_not_disturb_enabled?: boolean;
    display_name?: string;
    [key: string]: unknown;
};

export type PersistedPanePeer = {
    destination_hash: string;
    display_name: string | null;
    custom_display_name: string | null;
};

export type PersistedPaneState = {
    panes: Array<PersistedPanePeer | null>;
    sizes?: number[];
    focusedIndex?: number;
};

export type ConversationQueryInput = {
    conversationSearchTerm?: string | null;
    filterUnreadOnly?: boolean;
    filterFailedOnly?: boolean;
    filterHasAttachmentsOnly?: boolean;
    selectedFolderId?: number | string | null;
};

export type ConversationQueryParams = {
    search?: string;
    filter_unread?: boolean;
    filter_failed?: boolean;
    filter_has_attachments?: boolean;
    folder_id?: number | string;
};
