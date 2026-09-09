import DOMPurify from "dompurify";
import BaseMicronParser from "micron-parser";
import { inlineStyleHasNetworkPaint, scrubNetworkCss as scrubNetworkCssBody } from "./nomadCssSecurity.js";

const ALLOWED_URI_REGEXP =
    /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp|nomadnetwork|lxmf):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i;

const MICRON_IMAGE_FORMATTED_SIZE = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
});

const MICRON_IMAGE_MAX_WIDTH = 8192;
const MICRON_IMAGE_MAX_HEIGHT = 8192;
const MICRON_IMAGE_MAX_SIZE_HINT = 100 * 1024 * 1024; // 100 MiB
const MICRON_IMAGE_MAX_ALT_LEN = 240;
const MICRON_IMAGE_MAX_KEY_LEN = 64;
const MICRON_IMAGE_MAX_PROFILE_LEN = 32;
const MICRON_IMAGE_KEY_REGEXP = /^[a-zA-Z0-9_.-]*$/;
const MICRON_IMAGE_PROFILE_REGEXP = /^[a-zA-Z0-9_-]*$/;

function clampMicronImageNumber(value, max) {
    const n = Number(value);
    if (Number.isNaN(n)) {
        return null;
    }
    if (!Number.isFinite(n) || n <= 0) {
        return null;
    }
    return Math.min(Math.floor(n), max);
}

function sanitizeMicronImageString(value, maxLen, pattern = null) {
    if (typeof value !== "string") {
        return "";
    }
    const trimmed = value.trim();
    const limited = [...trimmed].slice(0, maxLen).join("");
    if (pattern && !pattern.test(limited)) {
        return "";
    }
    return limited;
}

function truncateMicronImageAlt(value) {
    if (typeof value !== "string") {
        return "";
    }
    return [...value.trim()].slice(0, MICRON_IMAGE_MAX_ALT_LEN).join("");
}

function parseMicronImageOptions(fields) {
    const options = {
        img: false,
        w: null,
        h: null,
        size: null,
        key: "",
        align: "left",
        profile: "",
    };
    if (!Array.isArray(fields)) {
        return options;
    }
    for (const raw of fields) {
        if (!raw || typeof raw !== "string") {
            continue;
        }
        const parts = raw.split(";");
        for (const part of parts) {
            const idx = part.indexOf("=");
            if (idx <= 0) {
                continue;
            }
            const k = part.slice(0, idx).trim().toLowerCase();
            const v = part.slice(idx + 1).trim();
            if (k === "img") {
                options.img = ["1", "true", "yes"].includes(v.toLowerCase());
            } else if (k === "w") {
                options.w = clampMicronImageNumber(v, MICRON_IMAGE_MAX_WIDTH);
            } else if (k === "h") {
                options.h = clampMicronImageNumber(v, MICRON_IMAGE_MAX_HEIGHT);
            } else if (k === "s") {
                options.size = clampMicronImageNumber(v, MICRON_IMAGE_MAX_SIZE_HINT);
            } else if (k === "k") {
                options.key = sanitizeMicronImageString(v, MICRON_IMAGE_MAX_KEY_LEN, MICRON_IMAGE_KEY_REGEXP);
            } else if (k === "a") {
                const av = v.toLowerCase();
                if (["left", "l"].includes(av)) {
                    options.align = "left";
                } else if (["center", "c"].includes(av)) {
                    options.align = "center";
                } else if (["right", "r"].includes(av)) {
                    options.align = "right";
                }
            } else if (k === "profile") {
                options.profile = sanitizeMicronImageString(
                    v,
                    MICRON_IMAGE_MAX_PROFILE_LEN,
                    MICRON_IMAGE_PROFILE_REGEXP
                );
            }
        }
    }
    return options;
}

function formatMicronImageSize(bytes) {
    if (bytes == null || bytes < 0) {
        return "";
    }
    if (bytes < 1024) {
        return String(bytes) + " B";
    }
    if (bytes < 1024 * 1024) {
        return MICRON_IMAGE_FORMATTED_SIZE.format(bytes / 1024) + " kB";
    }
    return MICRON_IMAGE_FORMATTED_SIZE.format(bytes / (1024 * 1024)) + " MB";
}

function escapeHtmlForFallback(text) {
    if (text == null) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Extends the published micron-parser with MeshChat / Nomad Network needs:
 * partial includes, overlay style stripping, wide CJK monospace cells, and lxmf/nomadnetwork in DOMPurify.
 */
export default class MicronParser extends BaseMicronParser {
    constructor(darkTheme = true, enableForceMonospace = true) {
        super(darkTheme, enableForceMonospace);
        if (this.enableForceMonospace) {
            const existing = document.getElementById("micron-monospace-styles");
            if (existing) {
                existing.remove();
            }
            this.injectMonospaceStyles();
        }
    }

    static get PARTIAL_LINE_REGEX() {
        // eslint-disable-next-line security/detect-unsafe-regex -- fixed pattern, bounded input (single line)
        return /^`\{([a-f0-9]{32}):([^`}]*)(?:`(\d+)(?:`([^}]*))?)?\}$/;
    }

    static isWideMonospaceCell(segment) {
        if (!segment) return false;
        if (
            /\p{Script=Han}|\p{Script=Hiragana}|\p{Script=Katakana}|\p{Script=Hangul}|\p{Script=Bopomofo}/u.test(
                segment
            )
        ) {
            return true;
        }
        const cp = segment.codePointAt(0);
        if (cp >= 0x3000 && cp <= 0x303f) return true;
        if (cp >= 0xff01 && cp <= 0xff5e) return true;
        if (cp >= 0xffe0 && cp <= 0xffe6) return true;
        return false;
    }

    /**
     * When false, forceMonospace can render a whole word in one span (Latin/Cyrillic/etc.),
     * avoiding one DOM node per character (critical for large pages and resize performance).
     */
    static lineNeedsPerCharCells(line) {
        if (!line) {
            return false;
        }
        for (const char of line) {
            if (MicronParser.isWideMonospaceCell(char)) {
                return true;
            }
            const cp = char.codePointAt(0);
            if (cp >= 0x2500 && cp <= 0x257f) {
                return true;
            }
            if (cp >= 0x2580 && cp <= 0x259f) {
                return true;
            }
        }
        return false;
    }

    static stripOverlayStyles(html) {
        if (typeof html !== "string") return html;
        const dangerousProps = ["zindex", "inset", "top", "left", "right", "bottom", "transform"];
        const scrubStyleValue = (styleValue) => {
            // Strip CSS comments so position/**/:fixed cannot hide the colon.
            let cleaned = String(styleValue).replace(/\/\*[\s\S]*?\*\//g, "");
            // Unescape simple CSS hex escapes (fixe\64 => fixed) used to hide overlays.
            cleaned = cleaned.replace(/\\([0-9a-fA-F]{1,6})\s?/g, (_, hex) => {
                try {
                    return String.fromCodePoint(parseInt(hex, 16));
                } catch {
                    return "";
                }
            });
            cleaned = cleaned.replace(/\\(.)/g, "$1");
            // Drop format/bidi noise so fi\u200Bxed / soft-hyphen cannot hide overlays.
            cleaned = cleaned.replace(/[\u00AD\u180E\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFEFF]/g, "");
            const declarations = cleaned.split(";").filter(Boolean);
            const safe = declarations.filter((decl) => {
                const colon = decl.indexOf(":");
                if (colon <= 0) return false;
                const rawProp = decl.slice(0, colon).trim();
                const prop = rawProp.toLowerCase().replace(/-/g, "").replace(/\s+/g, "");
                // Drop !important so "fixed !important" still matches fixed/sticky.
                const val = decl
                    .slice(colon + 1)
                    .trim()
                    .toLowerCase()
                    .replace(/!important/g, "")
                    .replace(/\s+/g, "")
                    .trim();
                if (
                    prop === "position" &&
                    (/\bfixed\b/.test(val) || /\bsticky\b/.test(val) || /\babsolute\b/.test(val))
                ) {
                    return false;
                }
                if (dangerousProps.includes(prop)) return false;
                // Block viewport-covering sizes. Keep width/height 100% for Micron
                // page and line backgrounds (NomadNet full-bleed rows).
                if (prop === "width" && /100v[wh]/.test(val)) return false;
                if (prop === "height" && /100v[hw]/.test(val)) return false;
                if (inlineStyleHasNetworkPaint(decl)) return false;
                return true;
            });
            return safe.join("; ").trim();
        };
        let out = html.replace(/(\s)style="([^"]*)"/gi, (match, space, styleValue) => {
            const scrubbed = scrubStyleValue(styleValue);
            return scrubbed ? `${space}style="${scrubbed}"` : "";
        });
        out = out.replace(/(\s)style='([^']*)'/gi, (match, space, styleValue) => {
            const scrubbed = scrubStyleValue(styleValue);
            return scrubbed ? `${space}style="${scrubbed}"` : "";
        });
        return out;
    }

    /**
     * Scrub network CSS from style tag bodies (WASM micron path).
     */
    static scrubNetworkCss(css) {
        return scrubNetworkCssBody(css);
    }

    static sanitizeRenderedMicronHtml(html) {
        if (html == null) {
            return "";
        }
        const s = typeof html === "string" ? html : String(html);
        try {
            let sanitized = DOMPurify.sanitize(s, {
                USE_PROFILES: { html: true },
                ALLOWED_URI_REGEXP,
            });
            try {
                sanitized = MicronParser.stripOverlayStyles(sanitized);
            } catch (e) {
                console.warn("MicronParser: stripOverlayStyles failed", e);
            }
            try {
                sanitized = MicronParser.scrubNetworkCssInStyleTags(sanitized);
            } catch (e) {
                console.warn("MicronParser: scrubNetworkCss failed", e);
            }
            return sanitized;
        } catch (error) {
            console.warn(
                "DOMPurify is not installed or sanitization failed. Include dompurify or check the build.",
                error
            );
            return `<p style="color: red;">DOMPurify is not installed or sanitization failed.</p>`;
        }
    }

    /**
     * Scrub network CSS inside &lt;style&gt; blocks without nested regex backtracking.
     */
    static scrubNetworkCssInStyleTags(html) {
        if (typeof html !== "string" || !html) {
            return html == null ? "" : html;
        }
        const lower = html.toLowerCase();
        let out = "";
        let i = 0;
        while (i < html.length) {
            const openIdx = lower.indexOf("<style", i);
            if (openIdx < 0) {
                out += html.slice(i);
                break;
            }
            const tagEnd = html.indexOf(">", openIdx);
            if (tagEnd < 0) {
                out += html.slice(i);
                break;
            }
            const closeIdx = lower.indexOf("</style>", tagEnd + 1);
            if (closeIdx < 0) {
                out += html.slice(i);
                break;
            }
            out += html.slice(i, tagEnd + 1);
            out += MicronParser.scrubNetworkCss(html.slice(tagEnd + 1, closeIdx));
            out += html.slice(closeIdx, closeIdx + "</style>".length);
            i = closeIdx + "</style>".length;
        }
        return out;
    }

    /**
     * Split Micron source into blocks for WASM conversion, keeping MeshChat partial-include lines on the JS path.
     */
    static splitMicronMarkupWasmSegments(markup) {
        if (markup == null) {
            return [];
        }
        const lines = String(markup).split("\n");
        const segments = [];
        let buf = [];
        for (const line of lines) {
            const trimmed = line.trim();
            if (MicronParser.PARTIAL_LINE_REGEX.test(trimmed)) {
                if (buf.length) {
                    segments.push({ type: "mu", text: buf.join("\n") });
                    buf = [];
                }
                segments.push({ type: "partial", line });
            } else {
                buf.push(line);
            }
        }
        if (buf.length) {
            segments.push({ type: "mu", text: buf.join("\n") });
        }
        return segments;
    }

    injectMonospaceStyles() {
        if (document.getElementById("micron-monospace-styles")) {
            return;
        }

        const styleEl = document.createElement("style");
        styleEl.id = "micron-monospace-styles";

        styleEl.textContent = `
            .Mu-nl {
                cursor: pointer;
                text-decoration: none;
            }
            .Mu-mnt {
                display: inline-block;
                box-sizing: border-box;
                width: 1ch;
                text-align: center;
                white-space: pre;
                text-decoration: inherit;
                vertical-align: baseline;
                line-height: 1.25;
            }
            .Mu-mnt-full {
                display: inline-block;
                box-sizing: border-box;
                width: 2ch;
                text-align: center;
                white-space: pre;
                text-decoration: inherit;
                vertical-align: baseline;
                line-height: 1.25;
            }
            .Mu-mws {
                text-decoration: inherit;
                display: inline-block;
                white-space: pre-wrap;
            }
            .Mu-mnt-group {
                display: inline;
                font-family: inherit;
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                word-break: break-word;
                text-decoration: inherit;
                vertical-align: baseline;
                line-height: 1.25;
            }
        `;
        document.head.appendChild(styleEl);
        MicronParser.installMicronCopyFix();
    }

    /**
     * Browsers insert newlines between adjacent inline-block Mu-mnt cells
     * when copying. Rebuild clipboard text without those spurious breaks while
     * keeping intentional block-level line breaks.
     */
    static installMicronCopyFix() {
        if (typeof document === "undefined" || window.__meshchatxMicronCopyFix) {
            return;
        }
        window.__meshchatxMicronCopyFix = true;
        document.addEventListener("copy", (event) => {
            const sel = window.getSelection();
            if (!sel || sel.isCollapsed || !sel.rangeCount) {
                return;
            }
            const anchor = sel.anchorNode;
            const focus = sel.focusNode;
            const anchorEl = anchor && anchor.nodeType === Node.ELEMENT_NODE ? anchor : anchor?.parentElement;
            const focusEl = focus && focus.nodeType === Node.ELEMENT_NODE ? focus : focus?.parentElement;
            const inMicron = (el) => Boolean(el?.closest?.(".Mu-mws, .Mu-mnt, .Mu-mnt-full, .Mu-mnt-group, .Mu-nl"));
            if (!inMicron(anchorEl) && !inMicron(focusEl)) {
                return;
            }
            try {
                const range = sel.getRangeAt(0);
                const fragment = range.cloneContents();
                const walker = document.createTreeWalker(fragment, NodeFilter.SHOW_ALL);
                let out = "";
                let node = walker.nextNode();
                while (node) {
                    if (node.nodeType === Node.TEXT_NODE) {
                        out += node.nodeValue || "";
                    } else if (node.nodeType === Node.ELEMENT_NODE) {
                        const tag = node.tagName;
                        if (tag === "BR" || tag === "DIV" || tag === "P" || tag === "PRE") {
                            if (out.length && !out.endsWith("\n")) {
                                out += "\n";
                            }
                        }
                    }
                    node = walker.nextNode();
                }
                // Collapse newlines that came only from adjacent inline-block cells.
                const cleaned = out.replace(/([^\n])\n(?!\n)/g, "$1");
                if (cleaned && event.clipboardData) {
                    event.clipboardData.setData("text/plain", cleaned);
                    event.preventDefault();
                }
            } catch {
                /* leave default copy behaviour */
            }
        });
    }

    convertMicronToHtmlWasmHybrid(markup, partialContents = {}) {
        const mc = globalThis.micronConvert;
        const segments = MicronParser.splitMicronMarkupWasmSegments(markup);
        let html = "";
        for (const seg of segments) {
            if (seg.type === "mu") {
                html += MicronParser.sanitizeRenderedMicronHtml(
                    mc(seg.text, this.darkTheme, this.enableForceMonospace)
                );
            } else {
                html += this._convertMicronToHtmlJs(seg.line + "\n", partialContents);
            }
        }
        return this._wrapMicronPageShell(markup, html);
    }

    /**
     * Match upstream micron-parser: when #!fg= / #!bg= headers are set, wrap
     * the page so the background fills the host (NomadNet full-page paint).
     * Also wraps with default theme fg (e.g. #ddd) like upstream.
     */
    _wrapMicronPageShell(markup, innerHtml) {
        let headerColors = { fg: null, bg: null };
        try {
            headerColors = this.parseHeaderTags(markup);
        } catch (e) {
            console.warn("MicronParser: parseHeaderTags failed", e);
        }
        const plainStyle = this.SELECTED_STYLES?.plain || { fg: this.DEFAULT_FG_DARK, bg: this.DEFAULT_BG };
        const defaultFg = headerColors.fg || plainStyle.fg;
        const defaultBg = headerColors.bg || plainStyle.bg;
        const hasFg = defaultFg && defaultFg !== "default";
        const hasBg = defaultBg && defaultBg !== "default";
        if (!hasFg && !hasBg) {
            return innerHtml;
        }
        const wrap = document.createElement("div");
        wrap.className = "mu-page";
        if (hasFg) {
            wrap.style.color = this.colorToCss(defaultFg);
        }
        if (hasBg) {
            wrap.style.backgroundColor = this.colorToCss(defaultBg);
        }
        wrap.innerHTML = innerHtml || "";
        return MicronParser.sanitizeRenderedMicronHtml(wrap.outerHTML);
    }

    _convertMicronToHtmlJs(markup, partialContents = {}) {
        const build = () => {
            let headerColors = { fg: null, bg: null };
            try {
                headerColors = this.parseHeaderTags(markup);
            } catch (e) {
                console.warn("MicronParser: parseHeaderTags failed", e);
            }

            const plainStyle = this.SELECTED_STYLES?.plain || { fg: this.DEFAULT_FG_DARK, bg: this.DEFAULT_BG };
            const defaultFg = headerColors.fg || plainStyle.fg;
            const defaultBg = headerColors.bg || plainStyle.bg;

            let state = {
                literal: false,
                depth: 0,
                fg_color: defaultFg,
                bg_color: defaultBg,
                formatting: {
                    bold: false,
                    underline: false,
                    italic: false,
                    strikethrough: false,
                },
                default_align: "left",
                align: "left",
                default_fg: defaultFg,
                default_bg: defaultBg,
                radio_groups: {},
                partialIndex: 0,
            };

            const lines = markup.split("\n");
            const tempContainer = document.createElement("div");
            const hasFg = defaultFg && defaultFg !== "default";
            const hasBg = defaultBg && defaultBg !== "default";
            if (hasFg || hasBg) {
                tempContainer.className = "mu-page";
            }
            if (hasFg) {
                tempContainer.style.color = this.colorToCss(defaultFg);
            }
            if (hasBg) {
                tempContainer.style.backgroundColor = this.colorToCss(defaultBg);
            }

            for (let line of lines) {
                let lineOutput;
                try {
                    lineOutput = this.parseLine(line, state);
                } catch (e) {
                    console.warn("MicronParser: parseLine failed", e);
                    const fallback = document.createElement("span");
                    fallback.className = "mu-line-parse-fallback";
                    fallback.style.whiteSpace = "pre-wrap";
                    fallback.innerHTML = escapeHtmlForFallback(line);
                    tempContainer.appendChild(fallback);
                    tempContainer.appendChild(document.createElement("br"));
                    continue;
                }
                if (lineOutput && lineOutput.length > 0) {
                    for (let el of lineOutput) {
                        try {
                            if (el.classList && el.classList.contains("mu-partial")) {
                                const id = el.getAttribute("data-partial-id");
                                if (id && partialContents[id]) {
                                    const holder = document.createElement("div");
                                    // Partials should arrive pre-sanitized, but do not
                                    // rely on every caller: sanitize at the sink too.
                                    holder.innerHTML = MicronParser.sanitizeRenderedMicronHtml(partialContents[id]);
                                    while (holder.firstChild) {
                                        tempContainer.appendChild(holder.firstChild);
                                    }
                                } else {
                                    tempContainer.appendChild(el);
                                }
                            } else {
                                tempContainer.appendChild(el);
                            }
                        } catch (e) {
                            console.warn("MicronParser: line output serialization failed", e);
                            const fallback = document.createElement("span");
                            fallback.className = "mu-line-parse-fallback";
                            fallback.style.whiteSpace = "pre-wrap";
                            fallback.innerHTML = escapeHtmlForFallback(line);
                            tempContainer.appendChild(fallback);
                            tempContainer.appendChild(document.createElement("br"));
                            break;
                        }
                    }
                } else if (lineOutput && lineOutput.length === 0) {
                    // skip
                } else {
                    tempContainer.appendChild(document.createElement("br"));
                }
            }

            try {
                if (typeof MicronParser._resolveEmptyAnchors === "function") {
                    MicronParser._resolveEmptyAnchors(tempContainer);
                }
            } catch (e) {
                console.warn("MicronParser: resolveEmptyAnchors failed", e);
            }

            const hasContainerStyle = hasFg || hasBg;
            const html = hasContainerStyle ? tempContainer.outerHTML : tempContainer.innerHTML;
            return MicronParser.sanitizeRenderedMicronHtml(html);
        };

        try {
            return build();
        } catch (e) {
            console.warn("MicronParser: convertMicronToHtml failed", e);
            const escaped = escapeHtmlForFallback(markup);
            try {
                return DOMPurify.sanitize(
                    `<pre class="mu-parse-fallback" style="white-space:pre-wrap">${escaped}</pre>`,
                    {
                        USE_PROFILES: { html: true },
                        ALLOWED_URI_REGEXP,
                    }
                );
            } catch {
                return `<pre class="mu-parse-fallback" style="white-space:pre-wrap">${escaped}</pre>`;
            }
        }
    }

    convertMicronToHtml(markup, partialContents = {}, options = {}) {
        if (markup == null) return "";
        if (typeof markup !== "string") markup = String(markup);

        const wantWasm = options.useWasm === true && typeof globalThis.micronConvert === "function";
        if (wantWasm) {
            try {
                return this.convertMicronToHtmlWasmHybrid(markup, partialContents);
            } catch (e) {
                console.warn("MicronParser: WASM Micron conversion failed, using JS parser", e);
            }
        }

        return this._convertMicronToHtmlJs(markup, partialContents);
    }

    convertMicronToFragment(markup) {
        if (markup == null) {
            return document.createDocumentFragment();
        }
        if (typeof markup !== "string") markup = String(markup);

        try {
            const fragment = document.createDocumentFragment();

            let headerColors = { fg: null, bg: null };
            try {
                headerColors = this.parseHeaderTags(markup);
            } catch (e) {
                console.warn("MicronParser: parseHeaderTags failed", e);
            }

            const plainStyle = this.SELECTED_STYLES?.plain || { fg: this.DEFAULT_FG_DARK, bg: this.DEFAULT_BG };
            const defaultFg = headerColors.fg || plainStyle.fg;
            const defaultBg = headerColors.bg || plainStyle.bg;

            let state = {
                literal: false,
                depth: 0,
                fg_color: defaultFg,
                bg_color: defaultBg,
                formatting: {
                    bold: false,
                    underline: false,
                    italic: false,
                    strikethrough: false,
                },
                default_align: "left",
                align: "left",
                default_fg: defaultFg,
                default_bg: defaultBg,
                radio_groups: {},
                partialIndex: 0,
            };

            const lines = markup.split("\n");

            for (let line of lines) {
                let sanitizedLine = line;
                try {
                    sanitizedLine = DOMPurify.sanitize(line, {
                        USE_PROFILES: { html: true },
                        ALLOWED_URI_REGEXP,
                    });
                } catch (e) {
                    console.warn("MicronParser: line sanitize failed", e);
                }
                let lineOutput;
                try {
                    lineOutput = this.parseLine(sanitizedLine, state);
                } catch (e) {
                    console.warn("MicronParser: parseLine failed", e);
                    const fallback = document.createElement("span");
                    fallback.className = "mu-line-parse-fallback";
                    fallback.style.whiteSpace = "pre-wrap";
                    fallback.textContent = line;
                    fragment.appendChild(fallback);
                    fragment.appendChild(document.createElement("br"));
                    continue;
                }
                if (lineOutput && lineOutput.length > 0) {
                    for (let el of lineOutput) {
                        try {
                            fragment.appendChild(el);
                        } catch (e) {
                            console.warn("MicronParser: appendChild failed", e);
                            const fallback = document.createElement("span");
                            fallback.className = "mu-line-parse-fallback";
                            fallback.style.whiteSpace = "pre-wrap";
                            fallback.textContent = line;
                            fragment.appendChild(fallback);
                            fragment.appendChild(document.createElement("br"));
                            break;
                        }
                    }
                } else if (lineOutput && lineOutput.length === 0) {
                    // skip
                } else {
                    fragment.appendChild(document.createElement("br"));
                }
            }

            return fragment;
        } catch (e) {
            console.warn("MicronParser: convertMicronToFragment failed", e);
            const fragment = document.createDocumentFragment();
            const pre = document.createElement("pre");
            pre.className = "mu-parse-fallback";
            pre.style.whiteSpace = "pre-wrap";
            pre.textContent = markup;
            fragment.appendChild(pre);
            return fragment;
        }
    }

    static parseImageOptions(fields) {
        return parseMicronImageOptions(fields);
    }

    static extractMicronImageFilePath(rawUrl) {
        // Strip the Nomad data-suffix backtick, query string or fragment before
        // checking the extension. Image links must point into the node file tree.
        if (typeof rawUrl !== "string" || !rawUrl) {
            return null;
        }
        let url = rawUrl.replace(/^nomadnetwork:\/\//i, "");
        url = url.split("`")[0].split("?")[0].split("#")[0].trim();
        // Accept "hash:/file/..." and relative ":/file/..." URLs.
        let path = url;
        let hash = "";
        if (url.includes(":/")) {
            const parts = url.split(":/");
            hash = parts[0];
            path = parts.slice(1).join(":/");
            if (hash && !/^[a-f0-9]{32}$/i.test(hash)) {
                return null;
            }
        } else if (url.startsWith(":")) {
            path = url.slice(1);
        }
        if (!path.startsWith("file/")) {
            return null;
        }
        if (!/\.webp$/i.test(path)) {
            return null;
        }
        // Reject anything that looks like traversal.
        if (path.includes("..") || [...path].some((ch) => ch.charCodeAt(0) < 32 || '<>"|?*'.includes(ch))) {
            return null;
        }
        if (hash) {
            return `${hash}:/${path}`;
        }
        return `:/${path}`;
    }

    parseLink(line, startIndex, state) {
        const linkData = super.parseLink(line, startIndex, state);
        if (!linkData || !linkData.obj) {
            return linkData;
        }
        const obj = linkData.obj;
        if (obj.type === "link" && Array.isArray(obj.fields) && obj.fields.length > 0) {
            const imgOptions = parseMicronImageOptions(obj.fields);
            if (imgOptions.img) {
                const rawUrl = String(obj.url || "").replace(/^nomadnetwork:\/\//, "");
                const imagePath = MicronParser.extractMicronImageFilePath(rawUrl);
                const endpos = line.indexOf("]", startIndex);
                let originalAlt = "";
                if (endpos >= 0) {
                    const linkDataRaw = line.substring(startIndex + 1, endpos);
                    const linkComponents = linkDataRaw.split("`");
                    if (linkComponents.length >= 2) {
                        originalAlt = linkComponents[0];
                    }
                }
                if (originalAlt.trim() && imagePath) {
                    obj.type = "image";
                    obj.alt = truncateMicronImageAlt(originalAlt.trim());
                    obj.rawUrl = rawUrl;
                    obj.imagePath = imagePath;
                    obj.imageOptions = imgOptions;
                }
            }
        }
        return linkData;
    }

    appendOutput(container, parts, state) {
        if (!Array.isArray(parts) || parts.length === 0) {
            return;
        }
        const flushNonImage = (chunk) => {
            if (chunk.length > 0) {
                super.appendOutput(container, chunk, state);
            }
        };
        let chunk = [];
        for (const p of parts) {
            if (p && p.type === "image") {
                flushNonImage(chunk);
                chunk = [];
                const el = this.createImagePlaceholder(p);
                if (el) {
                    container.appendChild(el);
                }
            } else {
                chunk.push(p);
            }
        }
        flushNonImage(chunk);
    }

    createImagePlaceholder(p) {
        if (!document) {
            return null;
        }
        const opts = p.imageOptions || {};
        const alt = truncateMicronImageAlt(p.alt || "");
        const url = p.rawUrl || "";
        const imagePath = p.imagePath || url;

        const div = document.createElement("div");
        div.className = "mu-image";
        div.setAttribute("data-mu-image-url", url);
        div.setAttribute("data-mu-image-path", imagePath);
        div.setAttribute("data-mu-image-alt", alt);
        if (opts.w != null) {
            div.setAttribute("data-mu-image-w", String(opts.w));
        }
        if (opts.h != null) {
            div.setAttribute("data-mu-image-h", String(opts.h));
        }
        if (opts.size != null) {
            div.setAttribute("data-mu-image-s", String(opts.size));
        }
        if (opts.key) {
            div.setAttribute("data-mu-image-k", opts.key);
        }
        if (opts.align) {
            div.setAttribute("data-mu-image-a", opts.align);
        }
        if (opts.profile) {
            div.setAttribute("data-mu-image-profile", opts.profile);
        }
        div.setAttribute("role", "img");
        div.setAttribute("aria-label", alt);

        if (opts.w != null) {
            div.style.width = String(opts.w) + "px";
        }
        if (opts.h != null) {
            div.style.minHeight = String(opts.h) + "px";
        }

        const meta = document.createElement("span");
        meta.className = "mu-image-meta";

        const altSpan = document.createElement("span");
        altSpan.className = "mu-image-alt";
        altSpan.textContent = alt;
        meta.appendChild(altSpan);

        if (opts.size != null && opts.size > 0) {
            meta.appendChild(document.createTextNode(" "));
            const sizeSpan = document.createElement("span");
            sizeSpan.className = "mu-image-size";
            sizeSpan.textContent = formatMicronImageSize(opts.size);
            meta.appendChild(sizeSpan);
        }

        const actions = document.createElement("span");
        actions.className = "mu-image-actions";

        const load = document.createElement("a");
        load.className = "mu-image-action";
        load.setAttribute("data-mu-image-action", "load");
        load.setAttribute("role", "button");
        load.setAttribute("tabindex", "0");
        load.textContent = "Load image";
        actions.appendChild(load);

        const img = document.createElement("img");
        img.className = "mu-image-output";
        img.setAttribute("alt", alt);
        img.setAttribute("hidden", "");

        div.appendChild(meta);
        div.appendChild(actions);
        div.appendChild(img);

        return div;
    }

    parseLine(line, state) {
        if (line.length > 0 && !state.literal) {
            const partialMatch = line.trim().match(MicronParser.PARTIAL_LINE_REGEX);
            if (partialMatch) {
                const dest = partialMatch[1];
                const path = partialMatch[2];
                const refresh = partialMatch[3] ? parseInt(partialMatch[3], 10) : null;
                const fields = partialMatch[4] || null;
                const id = "partial-" + state.partialIndex++;
                const div = document.createElement("div");
                div.className = "mu-partial";
                div.setAttribute("data-partial-id", id);
                div.setAttribute("data-dest", dest);
                div.setAttribute("data-path", path);
                if (refresh != null && refresh > 0) {
                    div.setAttribute("data-refresh", String(refresh));
                }
                if (fields) {
                    div.setAttribute("data-fields", fields);
                }
                div.textContent = "Loading...";
                return [div];
            }
        }
        return super.parseLine(line, state);
    }

    wrapWord(word) {
        if (word.length === 0) return "";
        if (!MicronParser.lineNeedsPerCharCells(word)) {
            return "<span class='Mu-mnt-group'>" + escapeHtmlForFallback(word) + "</span>";
        }
        let out = "";
        let charArr;
        try {
            charArr = [...new Intl.Segmenter().segment(word)].map((x) => x.segment);
        } catch {
            try {
                charArr = Array.from(word);
            } catch {
                charArr = word.split("");
            }
        }
        for (let char of charArr) {
            const cellClass = MicronParser.isWideMonospaceCell(char) ? "Mu-mnt-full" : "Mu-mnt";
            out += "<span class='" + cellClass + "'>" + escapeHtmlForFallback(char) + "</span>";
        }
        return "<span class='Mu-mws'>" + out + "</span>";
    }

    splitAtSpaces(line) {
        let out = "";
        const wordArr = line.split(/(?<= )/g);
        for (const word of wordArr) {
            out += this.wrapWord(word);
        }
        return out;
    }

    forceMonospace(line) {
        if (line == null || line === "") {
            return "";
        }
        if (!MicronParser.lineNeedsPerCharCells(line)) {
            return "<span class='Mu-mnt-group'>" + escapeHtmlForFallback(line) + "</span>";
        }
        let out = "";
        let charArr;
        try {
            charArr = [...new Intl.Segmenter().segment(line)].map((x) => x.segment);
        } catch {
            try {
                charArr = Array.from(line);
            } catch {
                charArr = line.split("");
            }
        }
        for (let char of charArr) {
            const cellClass = MicronParser.isWideMonospaceCell(char) ? "Mu-mnt-full" : "Mu-mnt";
            out += "<span class='" + cellClass + "'>" + escapeHtmlForFallback(char) + "</span>";
        }
        return out;
    }
}
