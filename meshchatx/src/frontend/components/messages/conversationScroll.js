export const SCROLL_BOTTOM_EPS_PX = 8;

export const LOAD_PREVIOUS_SCROLL_EDGE_PX = 500;

/**
 * The message list uses `flex-col-reverse` on the inner wrapper; scrollTop is 0 at the visual bottom
 * (newest messages) and increases toward older history.
 * @param {Element} container
 * @returns {boolean}
 */
export function isScrollColumnReverse(container) {
    const inner = container?.firstElementChild;
    if (!inner) {
        return false;
    }
    try {
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
