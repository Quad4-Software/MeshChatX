/**
 * Semantic design tokens for MeshChatX. CSS custom properties (--mc-*) are the
 * single source of truth for colors shared by Tailwind (`sem-*`), global CSS in
 * style.css, and the Vuetify theme (see vuetifyThemesFromTokens).
 */

const MESHCHAT_THEME_STYLE_ID = "meshchat-design-tokens";

/** @type {Record<string, string>} */
export const MESHCHAT_THEME_VARIABLES_LIGHT = {
    "--mc-canvas": "#f8fafc",
    "--mc-surface": "#ffffff",
    "--mc-border": "#e5e7eb",
    "--mc-border-card": "#e5e7eb",
    "--mc-border-strong": "#d1d5db",
    "--mc-text": "#111827",
    "--mc-text-secondary": "#1f2937",
    "--mc-text-muted": "#6b7280",
    "--mc-text-label": "#1f2937",
    "--mc-focus": "#60a5fa",
    "--mc-focus-border": "#60a5fa",
    "--mc-accent": "#2563eb",
    "--mc-accent-hover": "#3b82f6",
    "--mc-scrollbar-thumb": "#94a3b8",
    "--mc-scrollbar-track": "#e2e8f0",
    "--mc-scrollbar-thumb-border": "#e2e8f0",
    "--mc-glass-surface": "rgb(255 255 255 / 0.95)",
    "--mc-surface-muted": "rgb(249 250 251 / 0.9)",
    "--mc-surface-raised": "rgb(255 255 255 / 0.8)",
    "--mc-secondary-chip-bg": "#ffffff",
    "--mc-secondary-chip-text": "#374151",
    "--mc-secondary-chip-border": "#d1d5db",
    "--mc-secondary-chip-hover-bg": "#f9fafb",
    "--mc-secondary-chip-hover-text": "#111827",
    "--mc-secondary-chip-hover-border": "#60a5fa",
    "--mc-danger-chip-bg": "#fef2f2",
    "--mc-danger-chip-text": "#b91c1c",
    "--mc-danger-chip-border": "#fecaca",
    "--mc-danger-chip-hover-bg": "#fee2e2",
    "--mc-danger-chip-hover-text": "#991b1b",
    "--mc-input-option-bg": "#ffffff",
    "--mc-input-option-text": "#111827",
    "--mc-file-input-bg": "#f9fafb",
    "--mc-file-input-text": "#1f2937",
    "--mc-file-input-border": "#d1d5db",
    "--mc-address-action-bg": "#ffffff",
    "--mc-address-action-text": "#374151",
    "--mc-address-action-border": "#e5e7eb",
    "--mc-address-action-hover-bg": "#f9fafb",
    "--mc-address-action-hover-text": "#111827",
    "--mc-address-action-hover-border": "#60a5fa",
    "--mc-custom-scroll-thumb": "#cbd5e1",
    "--mc-custom-scroll-thumb-hover": "#94a3b8",
    "--mc-context-hover": "#f3f4f6",
    "--mc-context-divider": "#f3f4f6",
    "--mc-context-section": "#9ca3af",
    "--mc-context-item-text": "#374151",
    "--mc-info": "#0284c7",
    "--mc-success": "#16a34a",
    "--mc-warning": "#f97316",
    "--mc-error": "#dc2626",
};

/** @type {Record<string, string>} */
export const MESHCHAT_THEME_VARIABLES_DARK = {
    "--mc-canvas": "#09090b",
    "--mc-surface": "#18181b",
    "--mc-border": "#3f3f46",
    "--mc-border-card": "#27272a",
    "--mc-border-strong": "#52525b",
    "--mc-text": "#f3f4f6",
    "--mc-text-secondary": "#ffffff",
    "--mc-text-muted": "#9ca3af",
    "--mc-text-label": "#e5e7eb",
    "--mc-focus": "#3b82f6",
    "--mc-focus-border": "#3b82f6",
    "--mc-accent": "#60a5fa",
    "--mc-accent-hover": "#3b82f6",
    "--mc-scrollbar-thumb": "#52525b",
    "--mc-scrollbar-track": "#18181b",
    "--mc-scrollbar-thumb-border": "#18181b",
    "--mc-glass-surface": "rgb(24 24 27 / 0.85)",
    "--mc-surface-muted": "rgb(24 24 27 / 0.8)",
    "--mc-surface-raised": "rgb(24 24 27 / 0.7)",
    "--mc-secondary-chip-bg": "#18181b",
    "--mc-secondary-chip-text": "#f4f4f5",
    "--mc-secondary-chip-border": "#3f3f46",
    "--mc-secondary-chip-hover-bg": "#27272a",
    "--mc-secondary-chip-hover-text": "#ffffff",
    "--mc-secondary-chip-hover-border": "#3b82f6",
    "--mc-danger-chip-bg": "rgb(69 10 10 / 0.2)",
    "--mc-danger-chip-text": "#f87171",
    "--mc-danger-chip-border": "rgb(127 29 29 / 0.5)",
    "--mc-danger-chip-hover-bg": "rgb(127 29 29 / 0.4)",
    "--mc-danger-chip-hover-text": "#fca5a5",
    "--mc-input-option-bg": "#18181b",
    "--mc-input-option-text": "#f3f4f6",
    "--mc-file-input-bg": "#18181b",
    "--mc-file-input-text": "#f3f4f6",
    "--mc-file-input-border": "#3f3f46",
    "--mc-address-action-bg": "#18181b",
    "--mc-address-action-text": "#f4f4f5",
    "--mc-address-action-border": "#3f3f46",
    "--mc-address-action-hover-bg": "#27272a",
    "--mc-address-action-hover-text": "#ffffff",
    "--mc-address-action-hover-border": "#3b82f6",
    "--mc-custom-scroll-thumb": "#3f3f46",
    "--mc-custom-scroll-thumb-hover": "#52525b",
    "--mc-context-hover": "#27272a",
    "--mc-context-divider": "#27272a",
    "--mc-context-section": "#71717a",
    "--mc-context-item-text": "#e4e4e7",
    "--mc-info": "#38bdf8",
    "--mc-success": "#34d399",
    "--mc-warning": "#fb923c",
    "--mc-error": "#f87171",
};

/**
 * Tailwind theme.extend.colors.sem — uses the same --mc-* variables as style.css.
 * Keep keys in sync with usages in style.css and Vue (e.g. bg-sem-canvas).
 */
export function tailwindSemanticColorExtend() {
    return {
        canvas: "var(--mc-canvas)",
        surface: "var(--mc-surface)",
        border: "var(--mc-border)",
        "border-card": "var(--mc-border-card)",
        "border-strong": "var(--mc-border-strong)",
        fg: "var(--mc-text)",
        "fg-secondary": "var(--mc-text-secondary)",
        "fg-muted": "var(--mc-text-muted)",
        "fg-label": "var(--mc-text-label)",
        accent: "var(--mc-accent)",
        "accent-hover": "var(--mc-accent-hover)",
        focus: "var(--mc-focus)",
        glass: "var(--mc-glass-surface)",
        "surface-muted": "var(--mc-surface-muted)",
        "surface-raised": "var(--mc-surface-raised)",
        info: "var(--mc-info)",
        success: "var(--mc-success)",
        warning: "var(--mc-warning)",
        danger: "var(--mc-error)",
        "focus-border": "var(--mc-focus-border)",
        "file-input-bg": "var(--mc-file-input-bg)",
        "file-input-text": "var(--mc-file-input-text)",
    };
}

function serializeVarsBlock(vars) {
    return Object.entries(vars)
        .map(([k, v]) => `  ${k}: ${v};`)
        .join("\n");
}

/**
 * Injects :root and .dark variable blocks. Idempotent. Call once from main.js before mount.
 * @param {Document} [doc]
 */
export function injectMeshchatThemeVariables(doc = typeof document !== "undefined" ? document : null) {
    if (!doc?.head) {
        return;
    }
    const existing = doc.getElementById(MESHCHAT_THEME_STYLE_ID);
    if (existing) {
        existing.remove();
    }
    const el = doc.createElement("style");
    el.id = MESHCHAT_THEME_STYLE_ID;
    el.textContent = [
        ":root {",
        serializeVarsBlock(MESHCHAT_THEME_VARIABLES_LIGHT),
        "}",
        ".dark {",
        serializeVarsBlock(MESHCHAT_THEME_VARIABLES_DARK),
        "}",
    ].join("\n");
    doc.head.appendChild(el);
}

/**
 * Vuetify 3 theme definition derived from the same hexes as CSS light/dark tokens.
 */
export function vuetifyThemesFromTokens() {
    const L = MESHCHAT_THEME_VARIABLES_LIGHT;
    const D = MESHCHAT_THEME_VARIABLES_DARK;
    return {
        light: {
            dark: false,
            colors: {
                background: L["--mc-canvas"],
                surface: L["--mc-surface"],
                primary: L["--mc-accent"],
                secondary: "#475569",
                error: L["--mc-error"],
                info: L["--mc-info"],
                success: L["--mc-success"],
                warning: L["--mc-warning"],
            },
        },
        dark: {
            dark: true,
            colors: {
                background: D["--mc-canvas"],
                surface: D["--mc-surface"],
                primary: D["--mc-accent"],
                secondary: "#94a3b8",
                error: D["--mc-error"],
                info: D["--mc-info"],
                success: D["--mc-success"],
                warning: D["--mc-warning"],
            },
        },
    };
}
