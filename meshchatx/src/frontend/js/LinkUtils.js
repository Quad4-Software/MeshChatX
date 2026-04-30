import GlobalState from "./GlobalState.js";
import Utils from "./Utils.js";

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
        const anchors = [];
        const protectedText = text.replace(/<a\b[^>]*>[\s\S]*?<\/a>/gi, (anchor) => {
            const token = `[[ANCHOR_${anchors.length}]]`;
            anchors.push(anchor);
            return token;
        });
        return { protectedText, anchors };
    }

    static restoreAnchors(text, anchors) {
        return text.replace(/\[\[ANCHOR_(\d+)\]\]/g, (match, idx) => {
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
     * and bare <hash>:/path (NomadNet path form only — no bare hash without prefix).
     */
    static renderReticulumLinks(text) {
        if (!text) return "";

        // Hash is 32 hex chars. Path is optional (NomadNet only).
        const hashPattern = "[a-fA-F0-9]{32}";
        // Optional prefix, then hash, optional path. Bare hashes with no prefix and no
        // path are intentionally skipped to avoid false positives inside URLs.
        const reticulumRegex = new RegExp(
            `(nomadnet://|nomadnet@|lxmf://|lxmf@|lxmf:)?(${hashPattern})(?::(/[\\w\\d./?%&=_-]*))?`,
            "g"
        );

        return text.replace(reticulumRegex, (match, prefix, hash, path) => {
            if (!prefix && !path) {
                return match;
            }

            const isNomadNet =
                (prefix && (prefix.startsWith("nomadnet://") || prefix.startsWith("nomadnet@"))) || !!path;

            if (isNomadNet) {
                const fullPath = path || defaultNomadPagePath();
                const url = `${hash}:${fullPath}`;
                const safeAttr = Utils.escapeHtml(url);
                return `<a href="#" class="nomadnet-link text-blue-600 dark:text-blue-400 hover:underline font-mono" data-nomadnet-url="${safeAttr}">${match}</a>`;
            } else {
                return `<a href="#" class="lxmf-link text-blue-600 dark:text-blue-400 hover:underline font-mono" data-lxmf-address="${hash}">${match}</a>`;
            }
        });
    }

    /**
     * Basic URL detection for standard http/https links.
     */
    static renderStandardLinks(text) {
        if (!text) return "";

        const urlRegex = /(^|[^\w"'=])(https?:\/\/[^\s<'"]+)/g;
        return text.replace(urlRegex, (match, prefix, url) => {
            const { core, suffix } = this.splitTrailingPunctuation(url);
            if (!core) {
                return match;
            }
            const href = httpUrlHrefOrNull(core);
            if (!href) {
                return match;
            }
            const label = Utils.escapeHtml(core);
            return `${prefix}<a href="${href}" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">${label}</a>${suffix}`;
        });
    }

    /**
     * Applies all link rendering.
     */
    static renderAllLinks(text) {
        const { protectedText, anchors } = this.protectAnchors(text);
        let rendered = this.renderStandardLinks(protectedText);
        rendered = this.renderReticulumLinks(rendered);
        return this.restoreAnchors(rendered, anchors);
    }
}
