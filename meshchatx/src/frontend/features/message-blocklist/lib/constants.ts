// SPDX-License-Identifier: 0BSD

export const API_MESSAGE_BLOCKLIST = "/api/v1/lxmf/message-blocklist";
export const API_MESSAGE_BLOCKLIST_EXPORT = "/api/v1/lxmf/message-blocklist/export";
export const API_MESSAGE_BLOCKLIST_IMPORT = "/api/v1/lxmf/message-blocklist/import";

export const MESSAGE_BLOCKLIST_EXPORT_FILENAME = "meshchatx_message_blocklist.json";

export const DEFAULT_BLOCKLIST_SCOPE = "non_contacts" as const;
export const DEFAULT_BLOCKLIST_MATCH_MODE = "substring" as const;
export const DEFAULT_BLOCKLIST_MATCH_PEER_FIELDS = false;
export const DEFAULT_BLOCKLIST_MATCH_MESSAGE = true;

export const ID_RANDOM_RADIX = 16;
export const ID_SLICE_START = 2;
export const ID_SLICE_END = 18;
export const JSON_INDENT_SPACES = 2;
