// SPDX-License-Identifier: 0BSD

/**
 * Apply the configured UI font family. Called on boot and when the config changes.
 *
 * ui_font_family options:
 *   "system"   — browser default (Tailwind stack)
 *   "noto-sans" — bundled @fontsource/noto-sans
 *   "roboto-mono-nerd" — bundled RobotoMonoNerdFont
 *   "custom"   — user-uploaded font stored as base64 in ui_custom_font_data
 *
 * Custom font data is a base64-encoded woff2/ttf blob injected via @font-face.
 */

const FONT_STYLE_ID = "meshchat-font-loader";
const FONT_FACE_ID = "meshchat-custom-font-face";

const BUNDLED_FONTS = {
    "noto-sans": '"Noto Sans", ui-sans-serif, system-ui, sans-serif',
    "roboto-mono-nerd": '"Roboto Mono Nerd Font", ui-monospace, monospace',
};

/**
 * Inject or update the @font-face rule for a custom uploaded font.
 * @param {string} base64Data - base64-encoded font file bytes
 * @param {string} familyName - CSS font-family name to use
 */
export function injectCustomFontFace(base64Data, familyName) {
    if (typeof document === "undefined") return;
    const existing = document.getElementById(FONT_FACE_ID);
    if (existing) existing.remove();
    if (!base64Data) return;
    const el = document.createElement("style");
    el.id = FONT_FACE_ID;
    el.textContent = `@font-face {
    font-family: "${familyName.replace(/["\\]/g, "")}";
    src: url(data:font/woff2;base64,${base64Data}) format("woff2"),
         url(data:font/ttf;base64,${base64Data}) format("truetype"),
         url(data:font/otf;base64,${base64Data}) format("opentype");
    font-display: swap;
}`;
    document.head.appendChild(el);
}

/**
 * Apply the font-family to the document body.
 * @param {string} fontKey - "system" | bundled key | "custom"
 * @param {string} customFontName - name to use for the custom font family
 */
export function applyFontFamily(fontKey, customFontName = "MeshChatCustom") {
    if (typeof document === "undefined") return;
    const existing = document.getElementById(FONT_STYLE_ID);
    if (existing) existing.remove();

    let family = null;
    if (fontKey === "custom" && customFontName) {
        const sanitized = customFontName.replace(/["\\]/g, "");
        family = `"${sanitized}", ui-sans-serif, system-ui, sans-serif`;
    } else if (fontKey && fontKey !== "system") {
        family = BUNDLED_FONTS[fontKey] || null;
    }

    if (!family) return;

    const el = document.createElement("style");
    el.id = FONT_STYLE_ID;
    el.textContent = `body { font-family: ${family} !important; }`;
    document.head.appendChild(el);
}

/**
 * Read font config and apply it. Call after config loads and on config change.
 * @param {object} config - the config object from the store
 */
export function applyFontConfig(config) {
    if (!config) return;
    const fontKey = config.ui_font_family || "system";
    const customName = config.ui_custom_font_name || "MeshChatCustom";
    const customData = config.ui_custom_font_data || "";
    if (fontKey === "custom" && customData) {
        injectCustomFontFace(customData, customName);
    }
    applyFontFamily(fontKey, customName);
}

export { BUNDLED_FONTS };
