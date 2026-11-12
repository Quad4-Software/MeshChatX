// SPDX-License-Identifier: 0BSD

/**
 * Micron formatting in relay chat (RRC) message bodies, as NomadNet renders it.
 *
 * NomadNet runs a Markdown pass over chat bodies before Micron, and Markdown
 * treats backticks as inline code, so its chat syntax writes the Micron tag
 * character as U+00A6 BROKEN BAR instead of the backtick. Only that form is
 * recognised here: raw backtick Micron would collide with Markdown inline
 * code, which the plain chat renderer already uses.
 *
 * Supported tags: colour (¦Fxxx ¦Bxxx ¦FTxxxxxx ¦BTxxxxxx, ¦f ¦b back to the
 * default), bold ¦!, italic ¦*, underline ¦_ (toggles) and ¦` to reset all
 * formatting. Layout and link tags (¦< ¦> ¦{ ¦c ¦l ¦r ¦a ¦=) are dropped.
 * Any other ¦, including a lone one at the end, stays as text.
 *
 * Output is built from escaped text runs and colours taken only from the
 * parsed hex digits, so no markup from the message reaches the DOM.
 */

import LinkUtils from "../LinkUtils.js";
import Utils from "../Utils.js";

const TAG = "¦";

// Truecolour is tried before 12-bit.
const TAG_RE = /¦(?:([FB])T([0-9a-fA-F]{6})|([FB])([0-9a-fA-F]{3})|([fb!*_<>{clra=`]))/g;
const ANY_TAG_RE = /¦(?:[FB]T[0-9a-fA-F]{6}|[FB][0-9a-fA-F]{3}|[fb!*_<>{clra=`])/;
const COLOUR_TAG_RE = /¦[FB](?:T[0-9a-fA-F]{6}|[0-9a-fA-F]{3})/;

/**
 * True when the text carries at least one ¦-form Micron tag.
 * @param {unknown} text
 * @returns {boolean}
 */
export function hasRelayMicron(text) {
    return typeof text === "string" && text.includes(TAG) && ANY_TAG_RE.test(text);
}

/**
 * True when the text sets a Micron colour. Such messages are drawn as art:
 * monospace, whitespace kept exactly, no wrapping.
 * @param {unknown} text
 * @returns {boolean}
 */
export function hasRelayMicronColour(text) {
    return typeof text === "string" && text.includes(TAG) && COLOUR_TAG_RE.test(text);
}

function tokenize(text) {
    const tokens = [];
    let last = 0;
    for (const m of text.matchAll(TAG_RE)) {
        if (m.index > last) {
            tokens.push({ text: text.slice(last, m.index) });
        }
        last = m.index + m[0].length;
        if (m[1]) {
            tokens.push({ layer: m[1], color: m[2].toLowerCase() });
        } else if (m[3]) {
            tokens.push({ layer: m[3], color: m[4].toLowerCase() });
        } else {
            tokens.push({ op: m[5] });
        }
    }
    if (last < text.length) {
        tokens.push({ text: text.slice(last) });
    }
    return tokens;
}

/**
 * Remove every recognised ¦ tag and keep the text.
 * @param {unknown} text
 * @returns {string}
 */
export function stripRelayMicron(text) {
    if (text == null) {
        return "";
    }
    const s = String(text);
    if (!hasRelayMicron(s)) {
        return s;
    }
    return tokenize(s)
        .map((t) => t.text ?? "")
        .join("");
}

function styleFor(state) {
    const decls = [];
    if (state.fg) {
        decls.push(`color:#${state.fg}`);
    }
    if (state.bg) {
        decls.push(`background-color:#${state.bg}`);
    }
    if (state.bold) {
        decls.push("font-weight:bold");
    }
    if (state.italic) {
        decls.push("font-style:italic");
    }
    if (state.underline) {
        decls.push("text-decoration:underline");
    }
    return decls.join(";");
}

/**
 * Render a ¦-form Micron message body to HTML for the relay chat view.
 * Newlines are kept as text; the container sets the white-space mode.
 * @param {unknown} text
 * @returns {string}
 */
export function renderRelayMicronHtml(text) {
    if (text == null) {
        return "";
    }
    const state = { fg: null, bg: null, bold: false, italic: false, underline: false };
    let html = "";
    for (const token of tokenize(String(text))) {
        if (token.text !== undefined) {
            const body = LinkUtils.renderAllLinks(Utils.escapeHtml(token.text));
            const style = styleFor(state);
            html += style ? `<span style="${style}">${body}</span>` : body;
        } else if (token.layer === "F") {
            state.fg = token.color;
        } else if (token.layer === "B") {
            state.bg = token.color;
        } else if (token.op === "f") {
            state.fg = null;
        } else if (token.op === "b") {
            state.bg = null;
        } else if (token.op === "!") {
            state.bold = !state.bold;
        } else if (token.op === "*") {
            state.italic = !state.italic;
        } else if (token.op === "_") {
            state.underline = !state.underline;
        } else if (token.op === "`") {
            state.fg = null;
            state.bg = null;
            state.bold = false;
            state.italic = false;
            state.underline = false;
        }
        // Layout and link tags fall through and are dropped.
    }
    return html;
}
