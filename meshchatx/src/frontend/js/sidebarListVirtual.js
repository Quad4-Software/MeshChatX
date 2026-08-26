// SPDX-License-Identifier: 0BSD

/** Minimum row count before sidebar lists use @tanstack/vue-virtual. */
export const MIN_VIRTUAL_SIDEBAR_ITEMS = 32;

/** Default row height before measureElement runs. */
export const SIDEBAR_ROW_ESTIMATE_PX = 72;

/**
 * @param {unknown} _item
 * @returns {number}
 */
export function estimateSidebarRowHeight(_item) {
    return SIDEBAR_ROW_ESTIMATE_PX;
}
