// SPDX-License-Identifier: 0BSD

import { MESSAGE_BODY_MAX_DISPLAY_CHARS } from "../../../js/messageDisplayLimits.js";

/** Conversation history page size for /api/v1/lxmf-messages/conversation. */
export const CONVERSATION_MESSAGES_PAGE_SIZE = 50;

/** Use the virtual message list once display groups reach this count. */
export const MIN_VIRTUAL_DISPLAY_GROUPS = 48;

/** Near-bottom epsilon for auto-scroll decisions (px). */
export const SCROLL_BOTTOM_EPS_PX = 8;

/** Scroll position from top that triggers load-previous (px). */
export const LOAD_PREVIOUS_SCROLL_EDGE_PX = 500;

/** Max passes when settling scroll-to-bottom after open. */
export const SCROLL_SETTLE_MAX_PASSES = 24;

/** Keep pinning scroll to bottom this long after opening a conversation (ms). */
export const OPEN_CONVERSATION_SCROLL_PIN_MS = 900;

/** Cached decoded audio object URLs kept in memory. */
export const MAX_CACHED_AUDIO_ATTACHMENTS = 24;

/** Sticker attachment size cap (bytes). */
export const STICKER_MAX_BYTES = 512 * 1024;

/** GIF attachment size cap (bytes). */
export const GIF_MAX_BYTES = 2 * 1024 * 1024;

/** Confirm before enqueue when total outbound payload exceeds this (bytes). */
export const OUTBOUND_OVERSIZED_CONFIRM_BYTES = 900_000;

/** Max reaction chips shown before a "+N" overflow affordance. */
export const MAX_VISIBLE_REACTION_CHIPS = 4;

/** Auto-image caption is skipped above this content length. */
export const AUTO_IMAGE_CAPTION_MAX_CHARS = 240;

/** localStorage prefix for per-peer compose drafts. */
export const COMPOSE_DRAFT_STORAGE_PREFIX = "meshchatx.compose_draft.";

/** Legacy Vue drafts root (identity-scoped nested JSON object). */
export const LEGACY_COMPOSE_DRAFTS_STORAGE_KEY = "meshchat.drafts";

/** localStorage key for ingested paper-message hashes. */
export const PAPER_INGESTED_HASHES_STORAGE_KEY = "meshchatx.paper_ingested_hashes";

/** Cap stored paper-ingest hashes per identity. */
export const PAPER_INGESTED_HASHES_MAX_PER_IDENTITY = 500;

/** Fallback display name when peer announce has no name. */
export const ANONYMOUS_PEER_DISPLAY_NAME = "Anonymous Peer";

/** Height estimates for virtual list rows (px). */
export const VIRTUAL_ROW_HEIGHT = {
    default: 96,
    dateDivider: 44,
    imageGroup: 340,
    imageOnly: 280,
    base: 88,
} as const;

/** Re-export kernel inline body limit used by MessageEntry and raw modal. */
export { MESSAGE_BODY_MAX_DISPLAY_CHARS };
