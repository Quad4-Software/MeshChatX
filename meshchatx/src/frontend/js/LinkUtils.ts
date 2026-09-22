import GlobalState from "./GlobalState.js";
import Utils from "./Utils.js";
import { parseRelayUri } from "./relayLinkUtils.js";

function defaultNomadPagePath() {
    const p = GlobalState.config?.nomad_default_page_path;
    return typeof p === "string" && p.startsWith("/page/") ? p : "/page/index.mu";
}

function httpUrlHrefOrNull(core) {
    const tries = [core];
    if (core.includes("&amp;")) {
        tries.push(core.replace(/&amp;/g, "&"));
    }
    for (const candidate of tries) {
        try {
            const u = new URL(candidate);
            if (u.username || u.password) {
                return null;
            }
            if (u.protocol === "http:" || u.protocol === "https:") {
                return u.href;
            }
        } catch {
            /* try next */
        }
    }
    return null;
}

export default class LinkUtils {
    /**
     * Returns canonical http(s) href or null if the string is not a safe remote URL.
     */
    static httpUrlHrefOrNull(core) {
        return httpUrlHrefOrNull(core);
    }

    static protectAnchors(text) {
        const anchors: string[] = [];
        // The nonce keeps user-typed [[ANCHOR_n]] text from resolving to a
        // real anchor element at restore time.
        const nonce = Math.random().toString(36).slice(2);
        const protectedText = text.replace(/<a\b[^>]*>[\s\S]*?<\/a>/gi, (anchor) => {
            const token = `[[ANC_${nonce}_${anchors.length}]]`;
            anchors.push(anchor);
            return token;
        });
        return { protectedText, anchors, nonce };
    }

    static restoreAnchors(text, anchors, nonce) {
        // eslint-disable-next-line security/detect-non-literal-regexp -- nonce is generated, not user input
        const re = nonce ? new RegExp(`\\[\\[ANC_${nonce}_(\\d+)\\]\\]`, "g") : /\[\[ANCHOR_(\d+)\]\]/g;
        return text.replace(re, (match, idx) => {
            const i = Number(idx);
            return Number.isInteger(i) && i >= 0 && i < anchors.length ? anchors[i] : match;
        });
    }

    static splitTrailingPunctuation(url) {
        let core = url;
        let suffix = "";
        const alwaysTrim = new Set([".", ",", "!", "?", ":", ";"]);
        while (core.length > 0) {
            const ch = core.at(-1);
            if (alwaysTrim.has(ch)) {
                suffix = ch + suffix;
                core = core.slice(0, -1);
                continue;
            }
            if (ch === ")" || ch === "]") {
                const open = ch === ")" ? "(" : "[";
                const close = ch;
                const opens = [...core].filter((c) => c === open).length;
                const closes = [...core].filter((c) => c === close).length;
                if (closes > opens) {
                    suffix = ch + suffix;
                    core = core.slice(0, -1);
                    continue;
                }
            }
            break;
        }
        return { core, suffix };
    }

    /**
     * Detects and wraps Reticulum (NomadNet and LXMF) links in HTML.
     * Supports nomadnet://<hash>, nomadnet@<hash>, lxmf://<hash>, lxmf@<hash>, lxmf:<hash>,
     * and bare <hash>:/path (NomadNet path form only, no bare hash without prefix).
     */
    static renderReticulumLinks(text) {
        if (!text) return "";

        // Hash is 32 hex chars. Path is optional (NomadNet only).
        const hashPattern = "[a-fA-F0-9]{32}";
        // NomadNet paths may include field data after a backtick, e.g.
        // hash:/page/forum/thread.mu`cat=general|thread=slug
        // Path charset: URL path chars plus Nomad field separators (` | =).
        const pathPattern = "/[\\w./?%&=_+~|`-]*";
        // Optional prefix, then hash, optional path. Bare hashes with no prefix and no
        // path are intentionally skipped to avoid false positives inside URLs.
        const reticulumRegex = new RegExp(
            `(nomadnet://|nomadnet@|lxmf://|lxmf@|lxmf:)?(${hashPattern})(?::(${pathPattern}))?`,
            "g"
        );

        return text.replace(reticulumRegex, (match, prefix, hash, path) => {
            if (!prefix && !path) {
                return match;
            }

            const isNomadNet =
                (prefix && (prefix.startsWith("nomadnet://") || prefix.startsWith("nomadnet@"))) || !!path;

            if (isNomadNet) {
                const { core: pathCore, suffix: pathSuffix } = path
                    ? this.splitTrailingPunctuation(path)
                    : { core: "", suffix: "" };
                const fullPath = pathCore || defaultNomadPagePath();
                const url = `${hash}:${fullPath}`;
                const safeAttr = Utils.escapeHtml(url);
                const labelMatch = path ? `${prefix || ""}${hash}:${fullPath}` : match;
                const label = Utils.escapeHtml(labelMatch);
                return `<a href="#" class="nomadnet-link text-blue-600 dark:text-blue-400 hover:underline font-mono" data-nomadnet-url="${safeAttr}">${label}</a>${pathSuffix}`;
            } else {
                return `<a href="#" class="lxmf-link text-blue-600 dark:text-blue-400 hover:underline font-mono" data-lxmf-address="${hash}">${match}</a>`;
            }
        });
    }

    /**
     * Relay room deep links: meshchatx://relay?hub=&room= and the short
     * rrc://<hub_hash>/<room> form. Rendered as in-app action links carrying
     * the raw URI so the click handler can re-parse and join.
     */
    static renderRelayLinks(text) {
        if (!text) return "";
        const relayRegex = /(meshchatx|meshchat):\/\/relay\?[^\s<>"']+|rrc:\/\/[^\s<>"']+/gi;
        return text.replace(relayRegex, (match) => {
            let { core, suffix } = this.splitTrailingPunctuation(match);
            // Placeholder tokens ([[IC_n_0]] etc.) must never reach an
            // attribute value: the later restore pass would splice markup
            // containing quotes into data-rrc-url.
            const bracket = core.indexOf("[");
            if (bracket >= 0) {
                suffix = core.slice(bracket) + suffix;
                core = core.slice(0, bracket);
            }
            if (!core) {
                return match;
            }
            // Escaped entities adjacent to the URI (&#39; &quot;) carry no
            // literal terminator char, so the match can swallow them; strip
            // any trailing entity run before the &amp; fold. Single-entity
            // matches applied in a loop keep the pattern linear.
            const entityRe = /&[#a-zA-Z][\w]*;?$/;
            let entityTail;
            while ((entityTail = core.match(entityRe))) {
                suffix = entityTail[0] + suffix;
                core = core.slice(0, entityTail.index);
            }
            if (!core) {
                return match;
            }
            // Input text is already HTML-escaped, so &amp; must be folded back
            // before the URI can be parsed and stored.
            const rawCore = core.replace(/&amp;/g, "&");
            if (!parseRelayUri(rawCore)) {
                return match;
            }
            const safeAttr = Utils.escapeHtml(rawCore);
            const label = Utils.escapeHtml(rawCore);
            return `<a href="#" class="rrc-link text-blue-600 dark:text-blue-400 hover:underline font-mono" data-rrc-url="${safeAttr}">${label}</a>${suffix}`;
        });
    }

    /**
     * Basic URL detection for standard http/https links.
     */
    static renderStandardLinks(text) {
        if (!text) return "";

        const urlRegex = /(^|[^\w"'=])(https?:\/\/[^\s<'"]+)/g;
        return text.replace(urlRegex, (match, prefix, url) => {
            let { core, suffix } = this.splitTrailingPunctuation(url);
            // Placeholder tokens ([[IC_n_0]] etc.) must never reach an
            // attribute value: the later restore pass would splice markup
            // containing quotes into data-http-url.
            const bracket = core.indexOf("[");
            if (bracket >= 0) {
                suffix = core.slice(bracket) + suffix;
                core = core.slice(0, bracket);
            }
            if (!core) {
                return match;
            }
            const href = httpUrlHrefOrNull(core);
            if (!href) {
                return match;
            }
            const label = Utils.escapeHtml(core);
            // Keep real URL off href so middle-click / target=_blank cannot bypass
            // in-app stranger-link confirmation handlers.
            return `${prefix}<a href="#" data-http-url="${Utils.escapeHtml(href)}" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">${label}</a>${suffix}`;
        });
    }

    /**
     * Applies all link rendering.
     */
    static renderAllLinks(text) {
        const { protectedText, anchors, nonce } = this.protectAnchors(text);
        let rendered = this.renderStandardLinks(protectedText);
        rendered = this.renderRelayLinks(rendered);
        // renderStandardLinks / renderRelayLinks emit anchor markup whose
        // attribute values can hold 32-hex tokens. Shield them so the
        // reticulum pass cannot inject attributes into the generated anchors.
        const shielded = this.protectAnchors(rendered);
        rendered = this.renderReticulumLinks(shielded.protectedText);
        rendered = this.restoreAnchors(rendered, shielded.anchors, shielded.nonce);
        return this.restoreAnchors(rendered, anchors, nonce);
    }
}
