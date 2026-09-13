// SPDX-License-Identifier: 0BSD
/**
 * Shared network-CSS scrub for Micron and Nomad HTML style blocks.
 * Keeps color and layout decls. Blocks clearnet paint and modern wrappers
 * used in CSS exfiltration research (image-set, cross-fade, @import).
 */

/** Neutralise network and script-like CSS from a style sheet body. */
export function scrubNetworkCss(css: string): string {
    if (!css) {
        return "";
    }
    let s = String(css);
    s = s.replace(/@import\s+[^;]+;/gi, "");
    s = s.replace(/@import\s+url\s*\([^)]+\)\s*;?/gi, "");
    s = s.replace(/expression\s*\(/gi, "blocked(");
    s = s.replace(/javascript\s*:/gi, "blocked:");
    s = s.replace(/-moz-binding/gi, "blocked-binding");
    // Modern paint wrappers that still fetch urls inside (email CSS research).
    s = s.replace(/-webkit-image-set\s*\(/gi, "blocked(");
    s = s.replace(/image-set\s*\(/gi, "blocked(");
    s = s.replace(/cross-fade\s*\(/gi, "blocked(");
    s = s.replace(/url\s*\(\s*["']?(?:https?:|\/\/)/gi, "url(blocked:");
    return s;
}

/** True when an inline style declaration is a clearnet or scripted network paint. */
export function inlineStyleHasNetworkPaint(decl: string): boolean {
    const d = String(decl);
    if (/url\s*\(\s*["']?(?:https?:|\/\/)/i.test(d)) {
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
