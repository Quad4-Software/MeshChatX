/* SPDX-License-Identifier: 0BSD */

export const SCROLL_BOTTOM_EPS_PX = 8;

export const LOAD_PREVIOUS_SCROLL_EDGE_PX = 500;

/**
 * True only when inverted scrollTop math applies: scrollTop 0 is the visual bottom (newest).
 *
 * That is the classic pattern where the *scrolling element* (or its direct child) is
 * `flex-direction: column-reverse`. ConversationViewer now uses normal column flow for both
 * virtual and non-virtual lists (oldest at top, newest at bottom), so this returns false there.
 * @param {Element} container
 * @returns {boolean}
 */
export function isScrollColumnReverse(container) {
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

/**
 * Maximum valid scrollTop for a scroll container.
 * @param {Element} container
 * @returns {number}
 */
export function maxScrollTop(container) {
    if (!container) {
        return 0;
    }
    return Math.max(0, container.scrollHeight - container.clientHeight);
}

/**
 * Whether the viewport is within thresholdPx of the visual bottom (newest messages).
 * @param {Element} container
 * @param {number} [thresholdPx]
 * @returns {boolean}
 */
export function isNearBottom(container, thresholdPx = SCROLL_BOTTOM_EPS_PX) {
    if (!container) {
        return true;
    }
    if (isScrollColumnReverse(container)) {
        return container.scrollTop <= thresholdPx;
    }
    const max = maxScrollTop(container);
    return max - container.scrollTop <= thresholdPx;
}

/**
 * Sets scroll position to the visual bottom (newest messages).
 * @param {Element} container
 */
export function scrollContainerToBottom(container) {
    if (!container) {
        return;
    }
    if (isScrollColumnReverse(container)) {
        container.scrollTop = 0;
    } else {
        container.scrollTop = maxScrollTop(container);
    }
}

/**
 * Clears stale scroll position when reusing the same scroll element for another thread.
 * `scrollMessagesToBottom` / `scrollContainerToBottom` run after content is mounted.
 * @param {Element | null | undefined} container
 */
export function resetMessagesScrollSurface(container) {
    if (!container) {
        return;
    }
    container.scrollTop = 0;
}

/**
 * When the scroll area has no inner content yet, `isScrollColumnReverse` is false and
 * `isNearBottom` is misleading (empty scroller looks "at bottom"). Do not use it to settle.
 * @param {Element | null | undefined} container
 * @returns {boolean}
 */
export function canTrustScrollNearBottomHeuristic(container) {
    return Boolean(container?.firstElementChild);
}

/**
 * Whether the user has scrolled into the region where older messages should be loaded.
 * @param {Element} container
 * @returns {boolean}
 */
export function shouldLoadPreviousMessages(container) {
    if (!container) {
        return false;
    }
    if (isScrollColumnReverse(container)) {
        const max = maxScrollTop(container);
        if (max <= 0) {
            return false;
        }
        const st = container.scrollTop;
        if (max - st > LOAD_PREVIOUS_SCROLL_EDGE_PX) {
            return false;
        }
        // Short threads: `max - st` is small even at the visual bottom (newest), because `max` itself
        // is small. Require leaving the bottom band so we do not auto-load in a loop while pinned there.
        return st > SCROLL_BOTTOM_EPS_PX;
    }
    return container.scrollTop <= LOAD_PREVIOUS_SCROLL_EDGE_PX;
}
