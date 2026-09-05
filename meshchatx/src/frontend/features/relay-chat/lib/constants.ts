// SPDX-License-Identifier: 0BSD

export const BTN_PRIMARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg bg-sem-action-primary px-3 py-2 text-sm font-semibold text-white transition hover:bg-sem-action-primary-hover disabled:opacity-50 disabled:cursor-not-allowed";
export const BTN_SECONDARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg border border-sem-border bg-sem-surface-muted px-3 py-2 text-sm font-medium text-sem-fg transition hover:bg-sem-surface-raised disabled:opacity-50 disabled:cursor-not-allowed";
export const BTN_ICON =
    "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-2 text-sem-fg transition hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30 disabled:opacity-50 disabled:cursor-not-allowed";
export const BTN_ICON_SM =
    "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-1.5 text-sem-fg transition hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30";
export const BTN_DANGER =
    "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-2 text-sem-fg transition hover:border-sem-danger hover:text-sem-danger hover:bg-sem-danger/10 disabled:opacity-50 disabled:cursor-not-allowed";
export const BTN_DANGER_SM =
    "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-1.5 text-sem-fg transition hover:border-sem-danger hover:text-sem-danger hover:bg-sem-danger/10";

export const NAME_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6", "#3b82f6", "#8b5cf6", "#ec4899"];

export const LOAD_PREVIOUS_SCROLL_EDGE_PX = 200;
export const DEFAULT_ANNOUNCE_INTERVAL_SECONDS = 900;
export const ANNOUNCE_INTERVAL_MIN_MINUTES = 1;
export const ANNOUNCE_INTERVAL_MAX_MINUTES = 1440;
export const MIN_VIRTUAL_RELAY_ENTRIES = 150;
