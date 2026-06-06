// SPDX-License-Identifier: 0BSD

/** Relay Chat host moderation page layout (full-height, no modal shell). */

export const RELAY_HOST_PAGE_HEADER =
    "flex shrink-0 flex-wrap items-center gap-2 border-b border-sem-border bg-sem-canvas px-3 py-2.5 sm:px-4";

export const RELAY_HOST_PAGE_TABS = "flex shrink-0 gap-1.5 border-b border-sem-border bg-sem-canvas px-3 py-2 sm:px-4";

export const RELAY_HOST_PAGE_TAB =
    "inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors";

export const RELAY_HOST_PAGE_TAB_ACTIVE = "bg-sem-surface-raised text-sem-fg shadow-sm ring-1 ring-sem-border";

export const RELAY_HOST_PAGE_TAB_IDLE = "text-sem-fg-muted hover:bg-sem-surface-raised/60 hover:text-sem-fg";

export const RELAY_HOST_PAGE_BODY = "flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row";

export const RELAY_HOST_PAGE_LIST =
    "flex min-h-0 flex-col border-sem-border lg:w-80 lg:shrink-0 lg:border-r lg:bg-sem-surface-muted/20";

export const RELAY_HOST_PAGE_DETAIL = "flex min-h-0 min-w-0 flex-1 flex-col bg-sem-canvas";

export const RELAY_HOST_LIST_ITEM = "rounded-xl border border-sem-border bg-sem-surface-raised/50 transition-colors";

export const RELAY_HOST_LIST_ITEM_SELECTED = "border-sem-accent bg-sem-accent/15";

export const RELAY_HOST_LIST_ITEM_IDLE = "hover:bg-sem-surface-raised";

export const RELAY_HOST_DETAIL_HEADER =
    "shrink-0 border-b border-sem-border bg-sem-surface-muted/30 px-3 py-2.5 sm:px-4";

export const RELAY_HOST_MESSAGE =
    "rounded-lg border border-sem-border bg-sem-surface-raised px-3 py-2 text-sm text-sem-fg";

export const RELAY_HOST_ICON_BTN =
    "rounded-lg p-1.5 text-sem-fg-muted transition-colors hover:bg-sem-surface-raised hover:text-sem-fg";
