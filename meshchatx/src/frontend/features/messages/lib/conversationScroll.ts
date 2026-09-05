// SPDX-License-Identifier: 0BSD

import { LOAD_PREVIOUS_SCROLL_EDGE_PX, SCROLL_BOTTOM_EPS_PX } from "./constants.js";

export { LOAD_PREVIOUS_SCROLL_EDGE_PX, SCROLL_BOTTOM_EPS_PX };

/**
 * True only when inverted scrollTop math applies: scrollTop 0 is the visual bottom (newest).
 */
export function isScrollColumnReverse(container: Element | null | undefined): boolean {
    if (!container) {
        return false;
    }
    try {
        if (getComputedStyle(container).flexDirection === "column-reverse") {
            return true;
        }
        const inner = container.firstElementChild;
        if (!inner) {
            return false;
        }
        return getComputedStyle(inner).flexDirection === "column-reverse";
    } catch {
        return false;
    }
}

export function maxScrollTop(container: Element | null | undefined): number {
    if (!container) {
        return 0;
    }
    return Math.max(0, (container as HTMLElement).scrollHeight - (container as HTMLElement).clientHeight);
}

export function isNearBottom(container: Element | null | undefined, thresholdPx = SCROLL_BOTTOM_EPS_PX): boolean {
    if (!container) {
        return true;
    }
    const el = container as HTMLElement;
    if (isScrollColumnReverse(container)) {
        return el.scrollTop <= thresholdPx;
    }
    const max = maxScrollTop(container);
    return max - el.scrollTop <= thresholdPx;
}

export function scrollContainerToBottom(container: Element | null | undefined): void {
    if (!container) {
        return;
    }
    const el = container as HTMLElement;
    if (isScrollColumnReverse(container)) {
        el.scrollTop = 0;
    } else {
        el.scrollTop = maxScrollTop(container);
    }
}

export function resetMessagesScrollSurface(container: Element | null | undefined): void {
    if (!container) {
        return;
    }
    (container as HTMLElement).scrollTop = 0;
}

export function canTrustScrollNearBottomHeuristic(container: Element | null | undefined): boolean {
    return Boolean(container?.firstElementChild);
}

export function shouldLoadPreviousMessages(container: Element | null | undefined): boolean {
    if (!container) {
        return false;
    }
    const el = container as HTMLElement;
    if (isScrollColumnReverse(container)) {
        const max = maxScrollTop(container);
        if (max <= 0) {
            return false;
        }
        const st = el.scrollTop;
        if (max - st > LOAD_PREVIOUS_SCROLL_EDGE_PX) {
            return false;
        }
        return st > SCROLL_BOTTOM_EPS_PX;
    }
    return el.scrollTop <= LOAD_PREVIOUS_SCROLL_EDGE_PX;
}
