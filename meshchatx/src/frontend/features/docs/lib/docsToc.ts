// SPDX-License-Identifier: 0BSD

import type { DocTocEntry } from "./types.js";

/**
 * Extract table of contents headings from rendered HTML.
 */
export function extractDocToc(htmlContent: string): DocTocEntry[] {
    if (!htmlContent || typeof DOMParser === "undefined") {
        return [];
    }
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlContent, "text/html");
        return Array.from(doc.querySelectorAll("h2, h3"))
            .map((heading) => ({
                id: heading.id,
                text: heading.textContent?.trim() || "",
                level: (heading.tagName === "H2" ? 2 : 3) as 2 | 3,
            }))
            .filter((entry) => entry.id && entry.text);
    } catch {
        return [];
    }
}

/**
 * Smoothly scroll to a heading inside the prose container.
 */
export function scrollToHeadingInElement(container: HTMLElement | null, id: string): void {
    if (!container || typeof container.querySelector !== "function") {
        return;
    }
    if (!id || !/^[a-z0-9-]+$/.test(id)) {
        return;
    }
    const target = container.querySelector(`#${id}`);
    if (target && typeof target.scrollIntoView === "function") {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

/**
 * Highlight search query matches within snippet text.
 */
export function highlightMatch(text: string, searchQuery: string): string {
    if (!searchQuery) {
        return text;
    }

    const escapedText = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    const query = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    // eslint-disable-next-line security/detect-non-literal-regexp
    const regex = new RegExp(`(${query})`, "gi");
    return escapedText.replace(
        regex,
        '<span class="bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-0.5 rounded-sm">$1</span>'
    );
}

/**
 * Resolve relative markdown link path from current doc path.
 */
export function resolveRelativeDocPath(currentDocPath: string, href: string): string {
    const parts = (currentDocPath || "").split("/");
    parts.pop();

    const hrefParts = href.split("/");
    for (const part of hrefParts) {
        if (part === "..") {
            parts.pop();
        } else if (part !== ".") {
            parts.push(part);
        }
    }

    return parts.join("/");
}
