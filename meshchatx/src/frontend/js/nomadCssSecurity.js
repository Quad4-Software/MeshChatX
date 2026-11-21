// SPDX-License-Identifier: 0BSD
/**
 * Shared network-CSS scrub for Micron and Nomad HTML style blocks.
 * Keeps color and layout decls. Blocks clearnet paint and modern wrappers
 * used in CSS exfiltration research (image-set, cross-fade, @import).
 * Remote style blocks are also rendered into the main document (archive
 * viewer), so selectors that could match the host document (body, html,
 * :root) are rewritten onto the page wrapper classes.
 */

// Every render path wraps remote content in one of these classes, both in
// the sandboxed crash-tab frame and in the main-document archive viewer.
const PAGE_SCOPE = ":where(.mu-page,.nomad-markdown,.nomad-html-root)";

/**
 * Rewrite selectors that can match the host document so remote CSS only
 * applies inside the rendered page. Anchored on selector-start positions
 * (start, or after { } , ;) so declaration values, urls, and strings are
 * untouched. :not()/:has() args are left alone: negation and ancestor
 * matching cannot be scoped safely by token rewrite.
 *
 * @param {string} s
 * @returns {string}
 */
function scopeRemoteSelectors(s) {
    // "html body" and "html>body" describe the same page element; collapse
    // to a single token so the pair does not become two nested scopes.
    s = s.replace(/\bhtml\s+body\b/gi, "body");
    s = s.replace(/\bhtml\s*[>+~]\s*body\b/gi, "body");
    // html/body inside positive functional pseudo-classes still match the
    // real document element: :is(body) selects body itself. Runs before the
    // token pass below because the inserted :where() contains parens that
    // would break the [^()]* arg match.
    s = s.replace(
        /:(is|where|matches|-moz-any|-webkit-any)\(([^()]*)\)/gi,
        (m, fn, args) => `:${fn}(${String(args).replace(/(^|[\s,>+~(])(:root|html|body)\b/gi, `$1${PAGE_SCOPE}`)})`
    );
    s = s.replace(/(^|[{},;]\s*):root\b/gi, `$1${PAGE_SCOPE}`);
    s = s.replace(/(^|[{},;>+~]\s*)(html|body)(?=[\s>+~*:(.[#,){]|$)/gim, `$1${PAGE_SCOPE}`);
    return s;
}

/**
 * Neutralise network and script-like CSS from a style sheet body.
 *
 * @param {string} css
 * @returns {string}
 */
export function scrubNetworkCss(css) {
    if (!css) {
        return "";
    }
    let s = String(css);
    // Normalize evasions before matching: comments, CSS line continuations
    // (backslash+newline is deleted by the tokenizer, so "posi\<newline>tion"
    // is "position"), hex and simple escapes, and bidi/format noise.
    s = s.replace(/\/\*[\s\S]*?\*\//g, "");
    s = s.replace(/\\(?:\r\n|\r|\n)/g, "");
    s = s.replace(/\\([0-9a-fA-F]{1,6})\s?/g, (_, hex) => {
        try {
            return String.fromCodePoint(parseInt(hex, 16));
        } catch {
            return "";
        }
    });
    s = s.replace(/\\(.)/g, "$1");
    s = s.replace(/[\u00AD\u180E\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFEFF]/g, "");
    s = scopeRemoteSelectors(s);
    // @import takes a string or url() and does not require whitespace after
    // the at-keyword; remove through the next ; or { so media queries go too.
    s = s.replace(/@import\b[^;{]*/gi, "");
    s = s.replace(/expression\s*\(/gi, "blocked(");
    s = s.replace(/javascript\s*:/gi, "blocked:");
    s = s.replace(/-moz-binding/gi, "blocked-binding");
    // Modern paint wrappers that still fetch urls inside (email CSS research).
    s = s.replace(/-webkit-image-set\s*\(/gi, "blocked(");
    s = s.replace(/image-set\s*\(/gi, "blocked(");
    s = s.replace(/cross-fade\s*\(/gi, "blocked(");
    s = s.replace(/url\s*\(\s*["']?\s*(?:https?:|\/\/)/gi, "url(blocked:");
    return s;
}

/**
 * True when an inline style declaration is a clearnet or scripted network paint.
 *
 * @param {string} decl
 * @returns {boolean}
 */
export function inlineStyleHasNetworkPaint(decl) {
    const d = String(decl);
    if (/url\s*\(\s*["']?\s*(?:https?:|\/\/)/i.test(d)) {
        return true;
    }
    if (/@import/i.test(d)) {
        return true;
    }
    if (/expression\s*\(/i.test(d)) {
        return true;
    }
    if (/javascript\s*:/i.test(d)) {
        return true;
    }
    if (/-webkit-image-set\s*\(/i.test(d) || /image-set\s*\(/i.test(d) || /cross-fade\s*\(/i.test(d)) {
        return true;
    }
    return false;
}
