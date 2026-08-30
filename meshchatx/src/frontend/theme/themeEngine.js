// SPDX-License-Identifier: 0BSD

import { MESHCHAT_THEME_VARIABLES_DARK, MESHCHAT_THEME_VARIABLES_LIGHT } from "./designTokens.js";

export const THEME_PREFERENCE_VALUES = ["light", "dark", "system"];
export const THEME_PRESET_IDS = [
    "default",
    "high_contrast",
    "oled",
    "solarized",
    "nord",
    "gruvbox",
    "catppuccin",
    "dracula",
    "rose_pine",
    "forest",
    "midnight",
    "warm_paper",
    "tokyo",
    "atom_one",
    "neo_brutalist",
    "custom",
];

/** Settings UI order and i18n keys for color presets. */
export const THEME_PRESET_CATALOG = [
    { id: "default", labelKey: "app.theme_preset_default" },
    { id: "high_contrast", labelKey: "app.theme_preset_high_contrast" },
    { id: "oled", labelKey: "app.theme_preset_oled" },
    { id: "solarized", labelKey: "app.theme_preset_solarized" },
    { id: "nord", labelKey: "app.theme_preset_nord" },
    { id: "gruvbox", labelKey: "app.theme_preset_gruvbox" },
    { id: "catppuccin", labelKey: "app.theme_preset_catppuccin" },
    { id: "dracula", labelKey: "app.theme_preset_dracula" },
    { id: "rose_pine", labelKey: "app.theme_preset_rose_pine" },
    { id: "forest", labelKey: "app.theme_preset_forest" },
    { id: "midnight", labelKey: "app.theme_preset_midnight" },
    { id: "warm_paper", labelKey: "app.theme_preset_warm_paper" },
    { id: "tokyo", labelKey: "app.theme_preset_tokyo" },
    { id: "atom_one", labelKey: "app.theme_preset_atom_one" },
    { id: "neo_brutalist", labelKey: "app.theme_preset_neo_brutalist" },
    { id: "custom", labelKey: "app.theme_preset_custom" },
];

const MESHCHAT_THEME_OVERRIDES_STYLE_ID = "meshchat-theme-overrides";
const MESHCHAT_THEME_COLOR_META_ID = "meshchat-theme-color-meta";

/**
 * @param {unknown} value
 * @returns {"light" | "dark" | "system"}
 */
export function normalizeThemePreference(value) {
    if (value === "dark" || value === "system") {
        return value;
    }
    return "light";
}

/**
 * @param {unknown} value
 * @returns {string}
 */
export function normalizeThemePreset(value) {
    if (value === "hister") {
        return "neo_brutalist";
    }
    if (typeof value === "string" && THEME_PRESET_IDS.includes(value)) {
        return value;
    }
    return "default";
}

/**
 * @param {Window | null | undefined} windowObj
 * @returns {boolean}
 */
export function systemPrefersDark(windowObj = typeof window !== "undefined" ? window : null) {
    if (!windowObj?.matchMedia) {
        return false;
    }
    return windowObj.matchMedia("(prefers-color-scheme: dark)").matches;
}

/**
 * @param {unknown} themePreference
 * @param {boolean} [prefersDark]
 * @returns {"light" | "dark"}
 */
export function resolveEffectiveTheme(themePreference, prefersDark = systemPrefersDark()) {
    const pref = normalizeThemePreference(themePreference);
    if (pref === "dark") {
        return "dark";
    }
    if (pref === "system") {
        return prefersDark ? "dark" : "light";
    }
    return "light";
}

/**
 * @param {unknown} value
 * @returns {string | null}
 */
export function normalizeOptionalHexColor(value) {
    if (value == null || value === "") {
        return null;
    }
    if (typeof value === "string" && /^#[0-9A-Fa-f]{6}$/.test(value.trim())) {
        return value.trim();
    }
    return null;
}

/**
 * @param {string} hex
 * @returns {{ r: number, g: number, b: number } | null}
 */
export function parseHexColor(hex) {
    const normalized = normalizeOptionalHexColor(hex);
    if (!normalized) {
        return null;
    }
    return {
        r: parseInt(normalized.slice(1, 3), 16),
        g: parseInt(normalized.slice(3, 5), 16),
        b: parseInt(normalized.slice(5, 7), 16),
    };
}

/**
 * @param {number} r
 * @param {number} g
 * @param {number} b
 * @returns {string}
 */
export function rgbToHex(r, g, b) {
    const clamp = (n) => Math.max(0, Math.min(255, Math.round(n)));
    const part = (n) => clamp(n).toString(16).padStart(2, "0");
    return `#${part(r)}${part(g)}${part(b)}`;
}

/**
 * @param {string} hex
 * @param {number} amount
 * @returns {string}
 */
export function adjustHex(hex, amount) {
    const rgb = parseHexColor(hex);
    if (!rgb) {
        return hex;
    }
    return rgbToHex(rgb.r + amount, rgb.g + amount, rgb.b + amount);
}

/**
 * @param {string} a
 * @param {string} b
 * @param {number} ratio
 * @returns {string}
 */
export function mixHex(a, b, ratio = 0.5) {
    const left = parseHexColor(a);
    const right = parseHexColor(b);
    if (!left || !right) {
        return a;
    }
    return rgbToHex(
        left.r + (right.r - left.r) * ratio,
        left.g + (right.g - left.g) * ratio,
        left.b + (right.b - left.b) * ratio
    );
}

/**
 * @param {string} accentHex
 * @param {boolean} isDark
 * @returns {Record<string, string>}
 */
export function accentDerivativeVars(accentHex, isDark) {
    const hover = isDark ? adjustHex(accentHex, 20) : adjustHex(accentHex, 15);
    return {
        "--mc-accent": isDark ? mixHex(accentHex, "#ffffff", 0.25) : accentHex,
        "--mc-accent-hover": hover,
        "--mc-action-primary": accentHex,
        "--mc-action-primary-hover": hover,
        "--mc-focus": hover,
        "--mc-focus-border": hover,
        "--mc-secondary-chip-hover-border": hover,
        "--mc-address-action-hover-border": hover,
    };
}

/** @type {Record<string, { light: Record<string, string>, dark: Record<string, string> }>} */
export const THEME_PRESETS = {
    default: {
        light: {},
        dark: {},
    },
    high_contrast: {
        light: {
            "--mc-text": "#000000",
            "--mc-text-secondary": "#000000",
            "--mc-text-muted": "#374151",
            "--mc-border": "#000000",
            "--mc-border-card": "#000000",
            "--mc-border-strong": "#000000",
        },
        dark: {
            "--mc-text": "#ffffff",
            "--mc-text-secondary": "#ffffff",
            "--mc-text-muted": "#d4d4d8",
            "--mc-border": "#ffffff",
            "--mc-border-card": "#ffffff",
            "--mc-border-strong": "#ffffff",
        },
    },
    oled: {
        light: {
            "--mc-canvas": "#ffffff",
            "--mc-surface": "#fafafa",
            "--mc-border": "#e4e4e7",
            "--mc-border-card": "#e4e4e7",
            "--mc-text": "#09090b",
            "--mc-text-secondary": "#18181b",
            "--mc-text-muted": "#52525b",
        },
        dark: {
            "--mc-canvas": "#000000",
            "--mc-surface": "#000000",
            "--mc-border-card": "#141414",
            "--mc-glass-surface": "rgb(0 0 0 / 0.94)",
            "--mc-surface-muted": "rgb(20 20 20 / 0.9)",
            "--mc-surface-raised": "rgb(20 20 20 / 0.85)",
        },
    },
    solarized: {
        light: {
            "--mc-canvas": "#fdf6e3",
            "--mc-surface": "#eee8d5",
            "--mc-border": "#93a1a1",
            "--mc-text": "#073642",
            "--mc-text-secondary": "#073642",
            "--mc-text-muted": "#586e75",
            "--mc-accent": "#268bd2",
            "--mc-accent-hover": "#2aa198",
            "--mc-action-primary": "#268bd2",
            "--mc-action-primary-hover": "#2aa198",
        },
        dark: {
            "--mc-canvas": "#002b36",
            "--mc-surface": "#073642",
            "--mc-border": "#586e75",
            "--mc-text": "#fdf6e3",
            "--mc-text-secondary": "#eee8d5",
            "--mc-text-muted": "#93a1a1",
            "--mc-accent": "#2aa198",
            "--mc-accent-hover": "#268bd2",
            "--mc-action-primary": "#268bd2",
            "--mc-action-primary-hover": "#2aa198",
        },
    },
    nord: {
        light: {
            "--mc-canvas": "#eceff4",
            "--mc-surface": "#e5e9f0",
            "--mc-border": "#d8dee9",
            "--mc-border-card": "#d8dee9",
            "--mc-text": "#2e3440",
            "--mc-text-secondary": "#2e3440",
            "--mc-text-muted": "#4c566a",
            "--mc-accent": "#5e81ac",
            "--mc-accent-hover": "#81a1c1",
            "--mc-action-primary": "#5e81ac",
            "--mc-action-primary-hover": "#81a1c1",
        },
        dark: {
            "--mc-canvas": "#2e3440",
            "--mc-surface": "#3b4252",
            "--mc-border": "#4c566a",
            "--mc-border-card": "#434c5e",
            "--mc-text": "#eceff4",
            "--mc-text-secondary": "#e5e9f0",
            "--mc-text-muted": "#d8dee9",
            "--mc-accent": "#88c0d0",
            "--mc-accent-hover": "#8fbcbb",
            "--mc-action-primary": "#81a1c1",
            "--mc-action-primary-hover": "#88c0d0",
        },
    },
    gruvbox: {
        light: {
            "--mc-canvas": "#fbf1c7",
            "--mc-surface": "#ebdbb2",
            "--mc-border": "#d5c4a1",
            "--mc-border-card": "#d5c4a1",
            "--mc-text": "#3c3836",
            "--mc-text-secondary": "#504945",
            "--mc-text-muted": "#665c54",
            "--mc-accent": "#458588",
            "--mc-accent-hover": "#076678",
            "--mc-action-primary": "#458588",
            "--mc-action-primary-hover": "#076678",
        },
        dark: {
            "--mc-canvas": "#282828",
            "--mc-surface": "#3c3836",
            "--mc-border": "#504945",
            "--mc-border-card": "#504945",
            "--mc-text": "#ebdbb2",
            "--mc-text-secondary": "#d5c4a1",
            "--mc-text-muted": "#bdae93",
            "--mc-accent": "#83a598",
            "--mc-accent-hover": "#8ec07c",
            "--mc-action-primary": "#83a598",
            "--mc-action-primary-hover": "#8ec07c",
        },
    },
    catppuccin: {
        light: {
            "--mc-canvas": "#eff1f5",
            "--mc-surface": "#e6e9ef",
            "--mc-border": "#ccd0da",
            "--mc-border-card": "#ccd0da",
            "--mc-text": "#4c4f69",
            "--mc-text-secondary": "#5c5f77",
            "--mc-text-muted": "#6c6f85",
            "--mc-accent": "#1e66f5",
            "--mc-accent-hover": "#0284c7",
            "--mc-action-primary": "#1e66f5",
            "--mc-action-primary-hover": "#0284c7",
        },
        dark: {
            "--mc-canvas": "#1e1e2e",
            "--mc-surface": "#313244",
            "--mc-border": "#45475a",
            "--mc-border-card": "#45475a",
            "--mc-text": "#cdd6f4",
            "--mc-text-secondary": "#bac2de",
            "--mc-text-muted": "#a6adc8",
            "--mc-accent": "#89b4fa",
            "--mc-accent-hover": "#74c7ec",
            "--mc-action-primary": "#89b4fa",
            "--mc-action-primary-hover": "#74c7ec",
        },
    },
    dracula: {
        light: {
            "--mc-canvas": "#f8f8f2",
            "--mc-surface": "#ffffff",
            "--mc-border": "#e2e2dc",
            "--mc-border-card": "#e2e2dc",
            "--mc-text": "#282a36",
            "--mc-text-secondary": "#44475a",
            "--mc-text-muted": "#6272a4",
            "--mc-accent": "#7c6fbf",
            "--mc-accent-hover": "#6c5ce7",
            "--mc-action-primary": "#7c6fbf",
            "--mc-action-primary-hover": "#6c5ce7",
        },
        dark: {
            "--mc-canvas": "#282a36",
            "--mc-surface": "#44475a",
            "--mc-border": "#6272a4",
            "--mc-border-card": "#44475a",
            "--mc-text": "#f8f8f2",
            "--mc-text-secondary": "#f8f8f2",
            "--mc-text-muted": "#bd93f9",
            "--mc-accent": "#bd93f9",
            "--mc-accent-hover": "#ff79c6",
            "--mc-action-primary": "#bd93f9",
            "--mc-action-primary-hover": "#ff79c6",
        },
    },
    rose_pine: {
        light: {
            "--mc-canvas": "#faf4ed",
            "--mc-surface": "#fffaf3",
            "--mc-border": "#dfdad9",
            "--mc-border-card": "#dfdad9",
            "--mc-text": "#575279",
            "--mc-text-secondary": "#575279",
            "--mc-text-muted": "#797593",
            "--mc-accent": "#286983",
            "--mc-accent-hover": "#56949f",
            "--mc-action-primary": "#286983",
            "--mc-action-primary-hover": "#56949f",
        },
        dark: {
            "--mc-canvas": "#191724",
            "--mc-surface": "#1f1d2e",
            "--mc-border": "#403d52",
            "--mc-border-card": "#26233a",
            "--mc-text": "#e0def4",
            "--mc-text-secondary": "#e0def4",
            "--mc-text-muted": "#908caa",
            "--mc-accent": "#c4a7e7",
            "--mc-accent-hover": "#eb6f92",
            "--mc-action-primary": "#c4a7e7",
            "--mc-action-primary-hover": "#eb6f92",
        },
    },
    forest: {
        light: {
            "--mc-canvas": "#f0f7f4",
            "--mc-surface": "#ffffff",
            "--mc-border": "#b7e4c7",
            "--mc-border-card": "#b7e4c7",
            "--mc-text": "#1b4332",
            "--mc-text-secondary": "#2d6a4f",
            "--mc-text-muted": "#40916c",
            "--mc-accent": "#2d6a4f",
            "--mc-accent-hover": "#40916c",
            "--mc-action-primary": "#2d6a4f",
            "--mc-action-primary-hover": "#40916c",
        },
        dark: {
            "--mc-canvas": "#081c15",
            "--mc-surface": "#1b4332",
            "--mc-border": "#2d6a4f",
            "--mc-border-card": "#1b4332",
            "--mc-text": "#d8f3dc",
            "--mc-text-secondary": "#b7e4c7",
            "--mc-text-muted": "#95d5b2",
            "--mc-accent": "#52b788",
            "--mc-accent-hover": "#74c69d",
            "--mc-action-primary": "#52b788",
            "--mc-action-primary-hover": "#74c69d",
        },
    },
    midnight: {
        light: {
            "--mc-canvas": "#f0f4ff",
            "--mc-surface": "#ffffff",
            "--mc-border": "#c7d2fe",
            "--mc-border-card": "#c7d2fe",
            "--mc-text": "#1e293b",
            "--mc-text-secondary": "#334155",
            "--mc-text-muted": "#64748b",
            "--mc-accent": "#3b82f6",
            "--mc-accent-hover": "#2563eb",
            "--mc-action-primary": "#3b82f6",
            "--mc-action-primary-hover": "#2563eb",
        },
        dark: {
            "--mc-canvas": "#0f172a",
            "--mc-surface": "#1e293b",
            "--mc-border": "#334155",
            "--mc-border-card": "#1e293b",
            "--mc-text": "#e2e8f0",
            "--mc-text-secondary": "#cbd5e1",
            "--mc-text-muted": "#94a3b8",
            "--mc-accent": "#60a5fa",
            "--mc-accent-hover": "#38bdf8",
            "--mc-action-primary": "#60a5fa",
            "--mc-action-primary-hover": "#38bdf8",
        },
    },
    warm_paper: {
        light: {
            "--mc-canvas": "#faf6f0",
            "--mc-surface": "#fffdf8",
            "--mc-border": "#e7d8c9",
            "--mc-border-card": "#e7d8c9",
            "--mc-text": "#3d3229",
            "--mc-text-secondary": "#5c4a3d",
            "--mc-text-muted": "#8a7560",
            "--mc-accent": "#b45309",
            "--mc-accent-hover": "#d97706",
            "--mc-action-primary": "#b45309",
            "--mc-action-primary-hover": "#d97706",
        },
        dark: {
            "--mc-canvas": "#1c1917",
            "--mc-surface": "#292524",
            "--mc-border": "#44403c",
            "--mc-border-card": "#292524",
            "--mc-text": "#fafaf9",
            "--mc-text-secondary": "#e7e5e4",
            "--mc-text-muted": "#a8a29e",
            "--mc-accent": "#f59e0b",
            "--mc-accent-hover": "#fbbf24",
            "--mc-action-primary": "#f59e0b",
            "--mc-action-primary-hover": "#fbbf24",
        },
    },
    tokyo: {
        light: {
            "--mc-canvas": "#e6e7ea",
            "--mc-surface": "#d5d6db",
            "--mc-border": "#c0c2ca",
            "--mc-border-card": "#c0c2ca",
            "--mc-text": "#343b59",
            "--mc-text-secondary": "#343b59",
            "--mc-text-muted": "#565f89",
            "--mc-accent": "#295cdb",
            "--mc-accent-hover": "#188092",
            "--mc-action-primary": "#295cdb",
            "--mc-action-primary-hover": "#188092",
        },
        dark: {
            "--mc-canvas": "#1a1b26",
            "--mc-surface": "#24283b",
            "--mc-border": "#414868",
            "--mc-border-card": "#24283b",
            "--mc-text": "#c0caf5",
            "--mc-text-secondary": "#a9b1d6",
            "--mc-text-muted": "#737aa2",
            "--mc-accent": "#7aa2f7",
            "--mc-accent-hover": "#bb9af7",
            "--mc-action-primary": "#7aa2f7",
            "--mc-action-primary-hover": "#bb9af7",
        },
    },
    atom_one: {
        light: {
            "--mc-canvas": "#fafafa",
            "--mc-surface": "#ffffff",
            "--mc-border": "#e5e5e6",
            "--mc-border-card": "#e5e5e6",
            "--mc-text": "#383a42",
            "--mc-text-secondary": "#383a42",
            "--mc-text-muted": "#696c77",
            "--mc-accent": "#4078f2",
            "--mc-accent-hover": "#0184bc",
            "--mc-action-primary": "#4078f2",
            "--mc-action-primary-hover": "#0184bc",
        },
        dark: {
            "--mc-canvas": "#282c34",
            "--mc-surface": "#21252b",
            "--mc-border": "#3e4451",
            "--mc-border-card": "#21252b",
            "--mc-text": "#abb2bf",
            "--mc-text-secondary": "#abb2bf",
            "--mc-text-muted": "#828997",
            "--mc-accent": "#61afef",
            "--mc-accent-hover": "#56b6c2",
            "--mc-action-primary": "#61afef",
            "--mc-action-primary-hover": "#56b6c2",
        },
    },
    neo_brutalist: {
        light: {
            "--mc-canvas": "#f7f7f5",
            "--mc-surface": "#fafafa",
            "--mc-border": "#464b54",
            "--mc-border-card": "#464b54",
            "--mc-border-strong": "#2b2b2b",
            "--mc-text": "#2b2b2b",
            "--mc-text-secondary": "#2b2b2b",
            "--mc-text-muted": "#636363",
            "--mc-accent": "#8080c0",
            "--mc-accent-hover": "#2478ab",
            "--mc-action-primary": "#8080c0",
            "--mc-action-primary-hover": "#2478ab",
            "--mc-secondary-chip-hover-border": "#8080c0",
            "--mc-address-action-hover-border": "#8080c0",
        },
        dark: {
            "--mc-canvas": "#18191b",
            "--mc-surface": "#222428",
            "--mc-border": "#464b54",
            "--mc-border-card": "#2b2b2b",
            "--mc-border-strong": "#464b54",
            "--mc-text": "#eef0f3",
            "--mc-text-secondary": "#eef0f3",
            "--mc-text-muted": "#b9bec7",
            "--mc-accent": "#bc86dd",
            "--mc-accent-hover": "#5ab7ec",
            "--mc-action-primary": "#bc86dd",
            "--mc-action-primary-hover": "#5ab7ec",
            "--mc-secondary-chip-hover-border": "#bc86dd",
            "--mc-address-action-hover-border": "#bc86dd",
            "--mc-glass-surface": "rgb(34 36 40 / 0.92)",
            "--mc-surface-muted": "rgb(34 36 40 / 0.85)",
            "--mc-surface-raised": "rgb(34 36 40 / 0.7)",
        },
    },
    custom: {
        light: {},
        dark: {},
    },
};

/**
 * @param {string | null | undefined} canvasHex
 * @param {string | null | undefined} surfaceHex
 * @param {"light" | "dark"} effectiveMode
 * @returns {Record<string, string>}
 */
export function customThemeColorOverrides(canvasHex, surfaceHex, effectiveMode) {
    const canvas = normalizeOptionalHexColor(canvasHex);
    const surfaceInput = normalizeOptionalHexColor(surfaceHex);
    if (!canvas && !surfaceInput) {
        return {};
    }

    const isDark = effectiveMode === "dark";
    const overrides = {};
    if (canvas) {
        overrides["--mc-canvas"] = canvas;
    }
    if (surfaceInput) {
        overrides["--mc-surface"] = surfaceInput;
    }

    let resolvedSurface = overrides["--mc-surface"];
    if (canvas && surfaceInput && canvas.toLowerCase() === surfaceInput.toLowerCase()) {
        resolvedSurface = isDark ? adjustHex(surfaceInput, 14) : adjustHex(surfaceInput, -12);
        overrides["--mc-surface"] = resolvedSurface;
    }

    const canvasForMix =
        overrides["--mc-canvas"] ||
        (isDark ? MESHCHAT_THEME_VARIABLES_DARK["--mc-canvas"] : MESHCHAT_THEME_VARIABLES_LIGHT["--mc-canvas"]);
    const surfaceForMix =
        resolvedSurface ||
        overrides["--mc-surface"] ||
        (isDark ? MESHCHAT_THEME_VARIABLES_DARK["--mc-surface"] : MESHCHAT_THEME_VARIABLES_LIGHT["--mc-surface"]);
    const border = mixHex(canvasForMix, surfaceForMix, isDark ? 0.55 : 0.45);
    overrides["--mc-border"] = border;
    overrides["--mc-border-card"] = border;
    overrides["--mc-surface-muted"] = mixHex(canvasForMix, surfaceForMix, isDark ? 0.4 : 0.6);

    return overrides;
}

/**
 * @param {Record<string, unknown> | null | undefined} config
 * @param {"light" | "dark"} effectiveMode
 * @returns {Record<string, string>}
 */
export function buildThemeVariableOverrides(config, effectiveMode) {
    const presetId = normalizeThemePreset(config?.theme_preset);
    const preset = THEME_PRESETS[presetId] || THEME_PRESETS.default;
    const overrides = { ...(preset[effectiveMode] || {}) };

    if (presetId === "custom") {
        Object.assign(
            overrides,
            customThemeColorOverrides(config?.custom_canvas_color, config?.custom_surface_color, effectiveMode)
        );
    }

    const accent = normalizeOptionalHexColor(config?.accent_color);
    if (accent) {
        Object.assign(overrides, accentDerivativeVars(accent, effectiveMode === "dark"));
    }

    return overrides;
}

/**
 * @param {Record<string, unknown> | null | undefined} config
 * @param {"light" | "dark"} effectiveMode
 * @returns {string}
 */
export function resolveCanvasColor(config, effectiveMode) {
    const overrides = buildThemeVariableOverrides(config, effectiveMode);
    if (overrides["--mc-canvas"]) {
        return overrides["--mc-canvas"];
    }
    const base = effectiveMode === "dark" ? MESHCHAT_THEME_VARIABLES_DARK : MESHCHAT_THEME_VARIABLES_LIGHT;
    return base["--mc-canvas"];
}

/**
 * @param {string} hex
 * @returns {{ r: number, g: number, b: number, a: number }}
 */
export function hexToRgba(hex, alpha = 1) {
    const rgb = parseHexColor(hex);
    if (!rgb) {
        return { r: 248, g: 250, b: 252, a: alpha };
    }
    return { r: rgb.r, g: rgb.g, b: rgb.b, a: alpha };
}

/**
 * @param {Record<string, unknown> | null | undefined} config
 * @param {"light" | "dark"} effectiveMode
 * @returns {string}
 */
export function shellCanvasBackgroundStyle(config, effectiveMode) {
    const raw = Number(config?.ui_transparency ?? 0);
    const t = Number.isFinite(raw) ? Math.max(0, Math.min(100, raw)) : 0;
    const factor = t / 100;
    const alpha = 1 - factor * 0.42;
    const canvas = resolveCanvasColor(config, effectiveMode);
    const { r, g, b } = hexToRgba(canvas, alpha);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function serializeVarsBlock(vars) {
    return Object.entries(vars)
        .map(([k, v]) => `  ${k}: ${v};`)
        .join("\n");
}

/**
 * @param {Document | null | undefined} doc
 * @param {Record<string, string>} overrides
 * @param {"light" | "dark"} effectiveMode
 */
export function injectThemeOverrideVariables(
    doc = typeof document !== "undefined" ? document : null,
    overrides = {},
    effectiveMode = "light"
) {
    if (!doc?.head) {
        return;
    }
    doc.getElementById(MESHCHAT_THEME_OVERRIDES_STYLE_ID)?.remove();
    if (!overrides || Object.keys(overrides).length === 0) {
        return;
    }
    const selector = effectiveMode === "dark" ? ".dark" : ":root";
    const el = doc.createElement("style");
    el.id = MESHCHAT_THEME_OVERRIDES_STYLE_ID;
    el.textContent = [`${selector} {`, serializeVarsBlock(overrides), "}"].join("\n");
    doc.head.appendChild(el);
}

/**
 * @param {Document | null | undefined} doc
 * @param {string} canvasHex
 */
export function updateThemeColorMeta(doc = typeof document !== "undefined" ? document : null, canvasHex) {
    if (!doc?.head) {
        return;
    }
    let meta = doc.getElementById(MESHCHAT_THEME_COLOR_META_ID);
    if (!meta) {
        meta = doc.querySelector('meta[name="theme-color"]');
    }
    if (!meta) {
        meta = doc.createElement("meta");
        meta.setAttribute("name", "theme-color");
        meta.id = MESHCHAT_THEME_COLOR_META_ID;
        doc.head.appendChild(meta);
    } else if (!meta.id) {
        meta.id = MESHCHAT_THEME_COLOR_META_ID;
    }
    meta.setAttribute("content", canvasHex);
}

/**
 * @param {Record<string, unknown> | null | undefined} config
 * @param {object | null | undefined} options
 */
export function applyAppearanceTheme(config, options = {}) {
    const doc = options.doc ?? (typeof document !== "undefined" ? document : null);
    const windowObj = options.windowObj ?? (typeof window !== "undefined" ? window : null);
    const prefersDark = options.prefersDark !== undefined ? Boolean(options.prefersDark) : systemPrefersDark(windowObj);
    const effectiveMode = resolveEffectiveTheme(config?.theme, prefersDark);
    const preference = normalizeThemePreference(config?.theme);
    const overrides = buildThemeVariableOverrides(config, effectiveMode);

    if (doc?.documentElement) {
        doc.documentElement.classList.toggle("dark", effectiveMode === "dark");
        doc.documentElement.dataset.bootTheme = effectiveMode;
        doc.documentElement.dataset.themePreference = preference;
        doc.documentElement.style.colorScheme = effectiveMode;
    }

    injectThemeOverrideVariables(doc, overrides, effectiveMode);

    const canvasHex = resolveCanvasColor(config, effectiveMode);
    updateThemeColorMeta(doc, canvasHex);

    const persistMode = preference === "system" ? "system" : effectiveMode;
    try {
        windowObj?.localStorage?.setItem("meshchatx_ui_theme", persistMode);
    } catch {
        // ignore quota / private mode
    }

    try {
        const electronBridge = windowObj?.electron;
        if (electronBridge && typeof electronBridge.setUiTheme === "function") {
            void electronBridge.setUiTheme(persistMode);
        }
    } catch {
        // ignore missing bridge
    }

    try {
        const bridge = windowObj?.MeshChatXAndroid;
        if (bridge && typeof bridge.setUiTheme === "function") {
            bridge.setUiTheme(effectiveMode);
        }
    } catch {
        // ignore missing bridge
    }

    return {
        effectiveMode,
        preference,
        canvasHex,
        overrides,
    };
}

/**
 * @param {Window | null | undefined} windowObj
 * @param {(prefersDark: boolean) => void} callback
 * @returns {(() => void) | null}
 */
export function subscribeSystemTheme(windowObj = typeof window !== "undefined" ? window : null, callback) {
    if (!windowObj?.matchMedia) {
        return null;
    }
    const media = windowObj.matchMedia("(prefers-color-scheme: dark)");
    const handler = (event) => {
        callback(Boolean(event.matches));
    };
    if (typeof media.addEventListener === "function") {
        media.addEventListener("change", handler);
        return () => media.removeEventListener("change", handler);
    }
    media.addListener(handler);
    return () => media.removeListener(handler);
}

/**
 * @param {Record<string, unknown>} config
 */
export function sanitizeThemeConfigFields(config) {
    if (!config) {
        return;
    }
    config.theme = normalizeThemePreference(config.theme);
    config.theme_preset = normalizeThemePreset(config.theme_preset);
    config.accent_color = normalizeOptionalHexColor(config.accent_color);
    config.custom_canvas_color = normalizeOptionalHexColor(config.custom_canvas_color);
    config.custom_surface_color = normalizeOptionalHexColor(config.custom_surface_color);
}

/**
 * @param {Record<string, unknown> | null | undefined} config
 * @param {"light" | "dark"} effectiveMode
 * @returns {{ canvas: string, surface: string, accent: string, border: string }}
 */
export function getThemePresetPreviewColors(config, effectiveMode = "light") {
    const overrides = buildThemeVariableOverrides(config, effectiveMode);
    const base = effectiveMode === "dark" ? MESHCHAT_THEME_VARIABLES_DARK : MESHCHAT_THEME_VARIABLES_LIGHT;
    return {
        canvas: overrides["--mc-canvas"] || base["--mc-canvas"],
        surface: overrides["--mc-surface"] || base["--mc-surface"],
        accent:
            overrides["--mc-action-primary"] ||
            overrides["--mc-accent"] ||
            base["--mc-action-primary"] ||
            base["--mc-accent"],
        border: overrides["--mc-border-strong"] || overrides["--mc-border"] || base["--mc-border"],
    };
}

/**
 * @param {{ canvas: string, surface: string, accent: string, border: string }} colors
 * @returns {string}
 */
export function themePresetPreviewStripStyle(colors) {
    const canvas = colors.canvas || "#f8fafc";
    const surface = colors.surface || "#ffffff";
    const accent = colors.accent || "#2563eb";
    const border = colors.border || "#e5e7eb";
    return `linear-gradient(to right, ${canvas} 0% 25%, ${surface} 25% 50%, ${accent} 50% 75%, ${border} 75% 100%)`;
}
