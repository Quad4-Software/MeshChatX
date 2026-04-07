import DOMPurify from "dompurify";
import BaseMicronParser from "micron-parser";

const ALLOWED_URI_REGEXP =
    /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp|nomadnetwork|lxmf):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i;

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

    static stripOverlayStyles(html) {
        if (typeof html !== "string") return html;
        const dangerousProps = ["zindex", "inset", "top", "left", "right", "bottom", "transform"];
        return html.replace(/(\s)style="([^"]*)"/g, (match, space, styleValue) => {
            const declarations = styleValue.split(";").filter(Boolean);
            const safe = declarations.filter((decl) => {
                const colon = decl.indexOf(":");
                if (colon <= 0) return false;
                const rawProp = decl.slice(0, colon).trim();
                const prop = rawProp.toLowerCase().replace(/-/g, "");
                const val = decl
                    .slice(colon + 1)
                    .trim()
                    .toLowerCase();
                if (prop === "position" && (val === "fixed" || val === "sticky")) return false;
                if (dangerousProps.includes(prop)) return false;
                if (prop === "width" && /100v[wh]/.test(val)) return false;
                if (prop === "height" && /100v[hw]/.test(val)) return false;
                return true;
            });
            const out = safe.join("; ").trim();
            return out ? `${space}style="${out}"` : "";
        });
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
            }
            .Mu-mnt {
                display: inline-block;
                box-sizing: border-box;
                min-width: 1ch;
                width: 1ch;
                max-width: 1ch;
                text-align: center;
                white-space: pre;
                text-decoration: inherit;
                vertical-align: baseline;
                line-height: 1.25;
            }
            .Mu-mnt-full {
                display: inline-block;
                box-sizing: border-box;
                min-width: 2ch;
                width: 2ch;
                max-width: 2ch;
                text-align: center;
                white-space: pre;
                text-decoration: inherit;
                vertical-align: baseline;
                line-height: 1.25;
            }
            .Mu-mws {
                text-decoration: inherit;
                display: inline-flex;
                flex-wrap: wrap;
                align-items: baseline;
                column-gap: 0;
                row-gap: 0;
                gap: 0;
            }
        `;
        document.head.appendChild(styleEl);
    }

    convertMicronToHtml(markup, partialContents = {}) {
        if (markup == null) return "";
        if (typeof markup !== "string") markup = String(markup);

        const build = () => {
            let html = "";

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
                let lineOutput;
                try {
                    lineOutput = this.parseLine(line, state);
                } catch (e) {
                    console.warn("MicronParser: parseLine failed", e);
                    html += `<span class="mu-line-parse-fallback" style="white-space:pre-wrap">${escapeHtmlForFallback(line)}</span><br>`;
                    continue;
                }
                if (lineOutput && lineOutput.length > 0) {
                    for (let el of lineOutput) {
                        try {
                            if (el.classList && el.classList.contains("mu-partial")) {
                                const id = el.getAttribute("data-partial-id");
                                if (id && partialContents[id]) {
                                    html += partialContents[id];
                                } else {
                                    html += el.outerHTML;
                                }
                            } else {
                                html += el.outerHTML;
                            }
                        } catch (e) {
                            console.warn("MicronParser: line output serialization failed", e);
                            html += `<span class="mu-line-parse-fallback" style="white-space:pre-wrap">${escapeHtmlForFallback(line)}</span><br>`;
                            break;
                        }
                    }
                } else if (lineOutput && lineOutput.length === 0) {
                    // skip
                } else {
                    html += "<br>";
                }
            }

            try {
                const sanitized = DOMPurify.sanitize(html, {
                    USE_PROFILES: { html: true },
                    ALLOWED_URI_REGEXP,
                });
                try {
                    return MicronParser.stripOverlayStyles(sanitized);
                } catch (e) {
                    console.warn("MicronParser: stripOverlayStyles failed", e);
                    return sanitized;
                }
            } catch (error) {
                console.warn(
                    "DOMPurify is not installed or sanitization failed. Include dompurify or check the build.",
                    error
                );
                return `<p style="color: red;">DOMPurify is not installed or sanitization failed.</p>`;
            }
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

    forceMonospace(line) {
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
            out += "<span class='" + cellClass + "'>" + char + "</span>";
        }
        return out;
    }
}
