// SPDX-License-Identifier: 0BSD

export function safeFade(node: HTMLElement, { duration = 120 }: { duration?: number } = {}) {
    if (
        typeof window === "undefined" ||
        typeof node.animate !== "function" ||
        (typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches)
    ) {
        return { duration: 0 };
    }
    return {
        duration,
        css: (t: number) => `opacity: ${t}`,
    };
}
