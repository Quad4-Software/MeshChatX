// SPDX-License-Identifier: 0BSD

import type { ConversationQueryInput, ConversationQueryParams } from "./types.js";

/**
 * Build GET /api/v1/lxmf/conversations query params from sidebar filter state.
 */
export function buildConversationQueryParams(input: ConversationQueryInput = {}): ConversationQueryParams {
    const params: ConversationQueryParams = {};
    const search = input.conversationSearchTerm;
    if (search && String(search).trim() !== "") {
        params.search = String(search).trim();
    }
    if (input.filterUnreadOnly) {
        params.filter_unread = true;
    }
    if (input.filterFailedOnly) {
        params.filter_failed = true;
    }
    if (input.filterHasAttachmentsOnly) {
        params.filter_has_attachments = true;
    }
    if (input.selectedFolderId !== null && input.selectedFolderId !== undefined) {
        params.folder_id = input.selectedFolderId;
    }
    return params;
}
