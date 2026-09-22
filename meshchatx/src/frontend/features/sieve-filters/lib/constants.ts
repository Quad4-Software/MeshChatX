// SPDX-License-Identifier: 0BSD

export const DEFAULT_SIEVE_SCOPE = "everyone" as const;
export const DEFAULT_SIEVE_ACTION = "ignore" as const;
export const DEFAULT_SIEVE_MATCH_MODE = "substring" as const;

export const SIEVE_PALETTE = {
    src: { background: "#2563eb", border: "#1d4ed8", font: "#ffffff" },
    rule: { background: "#f4f4f5", border: "#a1a1aa", font: "#18181b" },
    ruleDark: { background: "#27272a", border: "#52525b", font: "#fafafa" },
    hide: { background: "#b91c1c", border: "#991b1b", font: "#ffffff" },
    ignore: { background: "#ca8a04", border: "#a16207", font: "#ffffff" },
    folder: { background: "#15803d", border: "#166534", font: "#ffffff" },
    banish: { background: "#4c1d95", border: "#5b21b6", font: "#ffffff" },
} as const;
