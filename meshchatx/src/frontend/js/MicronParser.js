import DOMPurify from "dompurify";
import BaseMicronParser from "micron-parser";

const ALLOWED_URI_REGEXP =
    /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp|nomadnetwork|lxmf):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i;

/**
 * Extends the published micron-parser with MeshChat / Nomad Network needs:
 * partial includes, overlay style stripping, wide CJK monospace cells, and lxmf/nomadnetwork in DOMPurify.
 */
export default class MicronParser extends BaseMicronParser {
    static MU_CELL_EM_NARROW = 0.72;
    static MU_CELL_EM_WIDE = 1.22;

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

        const n = MicronParser.MU_CELL_EM_NARROW;
        const w = MicronParser.MU_CELL_EM_WIDE;
        styleEl.textContent = `
            .Mu-nl {
                cursor: pointer;
            }
            .Mu-mnt {
                display: inline-block;
                box-sizing: border-box;
                min-width: ${n}em;
                width: ${n}em;
                text-align: center;
                white-space: pre;
                text-decoration: inherit;
                vertical-align: baseline;
                line-height: 1.45;
            }
            .Mu-mnt-full {
                display: inline-block;
                box-sizing: border-box;
                min-width: ${w}em;
                width: ${w}em;
                text-align: center;
                white-space: pre;
                text-decoration: inherit;
                vertical-align: baseline;
                line-height: 1.45;
            }
            .Mu-mws {
                text-decoration: inherit;
                display: inline-flex;
                flex-wrap: wrap;
                align-items: baseline;
                column-gap: 0.06em;
                row-gap: 0;
            }
        `;
        document.head.appendChild(styleEl);
    }

    convertMicronToHtml(markup, partialContents = {}) {
        if (markup == null) return "";
        if (typeof markup !== "string") markup = String(markup);
        let html = "";

        const headerColors = this.parseHeaderTags(markup);

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
            const lineOutput = this.parseLine(line, state);
            if (lineOutput && lineOutput.length > 0) {
                for (let el of lineOutput) {
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
            return MicronParser.stripOverlayStyles(sanitized);
        } catch (error) {
            console.warn(
                "DOMPurify is not installed. Include it above micron-parser.js or run npm install dompurify ",
                error
            );
            return `<p style="color: red;"> ⚠ DOMPurify is not installed. Include it above micron-parser.js or run npm install dompurify </p>`;
        }
    }

    convertMicronToFragment(markup) {
        const fragment = document.createDocumentFragment();

        const headerColors = this.parseHeaderTags(markup);

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
            line = DOMPurify.sanitize(line, {
                USE_PROFILES: { html: true },
                ALLOWED_URI_REGEXP,
            });
            const lineOutput = this.parseLine(line, state);
            if (lineOutput && lineOutput.length > 0) {
                for (let el of lineOutput) {
                    fragment.appendChild(el);
                }
            } else if (lineOutput && lineOutput.length === 0) {
                // skip
            } else {
                fragment.appendChild(document.createElement("br"));
            }
        }

        return fragment;
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
        const charArr = [...new Intl.Segmenter().segment(line)].map((x) => x.segment);
        for (let char of charArr) {
            const cellClass = MicronParser.isWideMonospaceCell(char) ? "Mu-mnt-full" : "Mu-mnt";
            out += "<span class='" + cellClass + "'>" + char + "</span>";
        }
        return out;
    }
}
