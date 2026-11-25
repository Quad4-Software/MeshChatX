// SPDX-License-Identifier: 0BSD
/**
 * Shared arithmetic for the Nomad browser touch gestures: left-edge swipe
 * back and pull-to-refresh. The sandboxed renderer frame and the shell page
 * container both run this logic, the frame forwards gesture progress through
 * postMessage, so the constants and dominance rules must match exactly.
 * Distances in CSS px.
 */

export const NAV_SWIPE_EDGE_PX = 40;
export const NAV_SWIPE_BACK_TRIGGER_PX = 64;
export const NAV_PULL_TRIGGER_PX = 72;
export const NAV_SWIPE_BACK_MAX_PX = 140;
export const NAV_PULL_MAX_PX = 160;

/**
 * Rightward horizontal-dominant motion continues an edge swipe-back.
 *
 * @param {number} dx horizontal displacement from the gesture start
 * @param {number} dy vertical displacement from the gesture start
 * @returns {boolean}
 */
export function isNavSwipeBackMotion(dx, dy) {
    return dx > 0 && dx > Math.abs(dy);
}

/**
 * Downward vertical-dominant motion continues a pull-to-refresh.
 *
 * @param {number} dx horizontal displacement from the gesture start
 * @param {number} dy vertical displacement from the gesture start
 * @returns {boolean}
 */
export function isNavPullMotion(dx, dy) {
    return dy > 0 && dy > Math.abs(dx);
}

/**
 * A touch may become a swipe-back only when it starts inside the left edge
 * zone and the scroller cannot pan right at that moment. With scrollLeft > 0
 * a rightward drag pans the content back natively, so forwarding it as
 * swipe-back would hijack the pan.
 *
 * @param {number} startX touch start x relative to the gesture surface
 * @param {number} scrollLeft horizontal scroll offset of the gesture surface
 * @returns {boolean}
 */
export function canArmNavSwipeBack(startX, scrollLeft) {
    return startX <= NAV_SWIPE_EDGE_PX && scrollLeft <= 0;
}

/**
 * Reversal-aware swipe-back distance: the motion must stay rightward-dominant
 * or the gesture is cancelled mid-flight and reports 0.
 *
 * @param {number} dx horizontal displacement from the gesture start
 * @param {number} dy vertical displacement from the gesture start
 * @returns {number}
 */
export function computeNavSwipeBackDistance(dx, dy) {
    return isNavSwipeBackMotion(dx, dy) ? Math.min(dx, NAV_SWIPE_BACK_MAX_PX) : 0;
}

/**
 * Reversal-aware pull distance: the scroller must have started at the top and
 * still be at the top, and the motion must stay downward-dominant.
 *
 * @param {number} dx horizontal displacement from the gesture start
 * @param {number} dy vertical displacement from the gesture start
 * @param {number} startScrollTop scroll offset when the gesture started
 * @param {number} scrollTop current scroll offset
 * @returns {number}
 */
export function computeNavPullDistance(dx, dy, startScrollTop, scrollTop) {
    if (startScrollTop > 0 || scrollTop > 0) {
        return 0;
    }
    return isNavPullMotion(dx, dy) ? Math.min(dy, NAV_PULL_MAX_PX) : 0;
}
